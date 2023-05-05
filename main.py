import chess
from stockfish import Stockfish
import openai
import random
import chess.pgn
from dotenv import load_dotenv  # Add this import
import os

print("Starting:")

# Set up your API key

OPEN_AI_API_KEY = os.getenv('OPEN_AI_API_KEY')
openai.api_key = OPEN_AI_API_KEY

def play_game(ai_move_func, engine_strength, max_tokens, retries):
    tokens_used = 0

    board = chess.Board()
    stockfish = Stockfish(parameters={"Skill Level": engine_strength})

    # Create a chess.pgn.Game object and set player names
    game = chess.pgn.Game()
    game.headers["White"] = "Chat GPT"
    game.headers["Black"] = f"Stockfish ({engine_strength})"

    # Create a chess.pgn.GameNode to record moves
    node = game

    while not board.is_game_over():
        if board.turn == chess.WHITE:
            move, tokens = ai_move_func(board, max_tokens, retries)
            tokens_used += tokens
        else:
            moves = board.move_stack
            stockfish.set_position([move.uci() for move in moves])
            move = chess.Move.from_uci(stockfish.get_best_move())

        # Add the move to the game node
        node = node.add_variation(move)

        # Push the move to the board
        board.push(move)

    # Set the result
    game.headers["Result"] = board.result()
    print(str(tokens_used))

    # Return the PGN
    return game

def gpt3_move(board, max_tokens, retries):
    moves_history = " ".join([move.uci() for move in board.move_stack])
    if moves_history == "":
        moves_history = "No moves have been made yet."

    for _ in range(retries):
        start_prompt = f"You are a chess bot, and you can ONLY reply in UCI notation. What is the best response in the current position? The game history is: {moves_history}. For example, 'd2d4' do not use punctuation!"
        prompt = f"Best response in the current position. The game history is: {moves_history}"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": start_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            n=1,
            stop=None,
            temperature=0.5,
        )

        move_str = response['choices'][0]['message']['content'].strip()

        # Print the response
        print(prompt)
        print(f"Response: {response['choices'][0]['message']['content']}")
        #print(f"Move: {move_str}")  # Print the move

        try:
            move = chess.Move.from_uci(move_str)
            if move in board.legal_moves:
                return move, response['usage']['total_tokens']

        except ValueError:
            pass

    # Make a random move if GPT-3 fails to provide a legal move after retries
    print('Making random move!')
    legal_moves = list(board.legal_moves)
    return random.choice(legal_moves), response['usage']['total_tokens']

def test_ai_elo(ai_move_func, initial_strength, max_strength, increment, games_per_strength, max_tokens, retries):
    games = []
    strength = initial_strength

    while strength <= max_strength:

        for _ in range(games_per_strength):
            game_pgn = play_game(ai_move_func, strength, max_tokens, retries)
            

            # Print the PGN of the game
            print(game_pgn)

        games.append(game_pgn)

        strength += increment

    return games


def estimate_token_usage(initial_strength, increment, games_per_strength, max_tokens=50, response_tokens=10, retries=3):
    num_strength_levels = (3000 - initial_strength) // increment
    num_games = num_strength_levels * games_per_strength
    ai_moves = num_games * 20  # Assuming an average of 20 moves per game for the AI
    total_tokens = ai_moves * (max_tokens + response_tokens) * retries
    return total_tokens


initial_strength = 0
max_strength = 500
increment = 250
games_per_strength = 1
max_tokens = 100
response_tokens = 100
retries = 1
cost_per_1000_tokens = 0.06
cost_per_token = cost_per_1000_tokens/1000

token_usage = estimate_token_usage(
    initial_strength, increment, games_per_strength, max_tokens=30, retries=retries)
print(f"Estimated token usage: {token_usage}")

total_cost = token_usage * cost_per_token
print(f"Estimated total cost: ${total_cost:.2f}")

if int(total_cost) > 50:
    print("Over $50, that's nuts I'm terminating the program for you :)")
    exit()

if input("Type y to continue? Be fucking careful! ") != "y":
    exit()

# Test the AI's Elo rating
games = test_ai_elo(gpt3_move, initial_strength, max_strength, increment,
                      games_per_strength, max_tokens, retries)

# Print the results
for r in games:
    result = r.headers["Result"]
    print()