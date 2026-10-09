# Rock Paper Scissors player.
#
# Strategy: an ensemble of predictors. Each predictor guesses the opponent's
# next move. We keep a running (decaying) score of how often each predictor
# has been right in the current match and play the move that beats the
# prediction of the best-scoring predictor. State resets at the start of
# every match (when prev_play is the empty string).

BEATS = {"R": "P", "P": "S", "S": "R"}  # move that beats the key
MOVES = ["R", "P", "S"]

state = {}


def _reset():
    state.clear()
    state["mine"] = []        # my moves this match
    state["theirs"] = []      # opponent moves this match
    state["scores"] = {}      # predictor name -> decayed score
    state["last_pred"] = {}   # predictor name -> its last prediction


# ---------- predictors (each returns the opponent's predicted next move) ----

def _pred_counter_my_last(mine, theirs):
    # Opponent plays whatever beats my previous move.
    last = mine[-1] if mine else "R"
    return BEATS[last]


def _pred_counter_my_frequent(mine, theirs):
    # Opponent plays whatever beats my most frequent move over my last 10.
    last_ten = ([""] + mine)[-10:]
    most = max(set(last_ten), key=last_ten.count)
    if most == "":
        most = "S"
    return BEATS[most]


def _pred_markov_on_me(mine, theirs):
    # Opponent predicts my next move from pairs of my consecutive moves
    # and plays the counter to it.
    hist = ["R"] + mine
    counts = {a + b: 0 for a in MOVES for b in MOVES}
    for i in range(len(hist) - 1):
        counts[hist[i] + hist[i + 1]] += 1
    last = hist[-1]
    options = [last + m for m in MOVES]
    guess = max(options, key=lambda k: counts[k])[-1]
    return BEATS[guess]


def _make_cycle_pred(period):
    def pred(mine, theirs):
        if len(theirs) >= period:
            return theirs[-period]
        return None
    return pred


def _make_ngram_pred(n):
    # Predict opponent's next move from what followed their last n moves.
    def pred(mine, theirs):
        if len(theirs) <= n:
            return None
        key = tuple(theirs[-n:])
        counts = {m: 0 for m in MOVES}
        for i in range(len(theirs) - n):
            if tuple(theirs[i:i + n]) == key:
                counts[theirs[i + n]] += 1
        if max(counts.values()) == 0:
            return None
        return max(counts, key=counts.get)
    return pred


def _make_joint_pred(n):
    # Predict opponent's reply from the last n (my move, their move) pairs.
    def pred(mine, theirs):
        k = len(theirs)
        if k <= n or len(mine) < k:
            return None
        pairs = list(zip(mine[:k], theirs))
        key = tuple(pairs[-n:])
        counts = {m: 0 for m in MOVES}
        for i in range(k - n):
            if tuple(pairs[i:i + n]) == key:
                counts[theirs[i + n]] += 1
        if max(counts.values()) == 0:
            return None
        return max(counts, key=counts.get)
    return pred


PREDICTORS = {
    "counter_last": _pred_counter_my_last,
    "counter_freq": _pred_counter_my_frequent,
    "markov_me": _pred_markov_on_me,
}
for _p in range(2, 7):
    PREDICTORS["cycle%d" % _p] = _make_cycle_pred(_p)
for _n in range(1, 5):
    PREDICTORS["ngram%d" % _n] = _make_ngram_pred(_n)
for _n in range(1, 3):
    PREDICTORS["joint%d" % _n] = _make_joint_pred(_n)

DECAY = 0.9


def player(prev_play, opponent_history=[]):
    if prev_play == "" or not state:
        _reset()
    else:
        state["theirs"].append(prev_play)
        opponent_history.append(prev_play)
        # Score last round's predictions.
        for name, guess in state["last_pred"].items():
            s = state["scores"].get(name, 0.0) * DECAY
            if guess is not None:
                s += 1.0 if guess == prev_play else -0.5
            state["scores"][name] = s

    mine, theirs = state["mine"], state["theirs"]

    preds = {name: fn(mine, theirs) for name, fn in PREDICTORS.items()}
    state["last_pred"] = preds

    best_name, best_score = None, float("-inf")
    for name, guess in preds.items():
        if guess is None:
            continue
        score = state["scores"].get(name, 0.0)
        if score > best_score:
            best_name, best_score = name, score

    if best_name is None:
        move = "P"
    else:
        move = BEATS[preds[best_name]]

    mine.append(move)
    return move
