import numpy as np

from rl.behavior_cloning import _accuracy, generate_dataset, train_bc
from rl.obs_encoding import OBS_SIZE


def test_dataset_shapes_and_label_legality():
    data = generate_dataset(num_games=8, eps=0.3, seed=1)
    n = len(data["actions"])
    assert n > 0
    assert data["obs"].shape == (n, OBS_SIZE)
    assert data["masks"].shape == (n, 51)
    assert set(np.unique(data["decisions"])) <= {1, 2, 3}
    # Every label must be a legal action in the state it was recorded in.
    assert data["masks"][np.arange(n), data["actions"]].all()


def test_dataset_generation_is_deterministic_per_seed():
    a = generate_dataset(num_games=5, eps=0.2, seed=7)
    b = generate_dataset(num_games=5, eps=0.2, seed=7)
    for key in a:
        assert np.array_equal(a[key], b[key])
    c = generate_dataset(num_games=5, eps=0.2, seed=8)
    assert not np.array_equal(a["obs"][:1], c["obs"][:1]) or len(a["actions"]) != len(c["actions"])


def test_random_exploration_changes_visited_states_but_not_labels_source():
    # eps controls only which action is *executed*; labels are always the heuristic's.
    greedy = generate_dataset(num_games=5, eps=0.0, seed=3)
    noisy = generate_dataset(num_games=5, eps=0.9, seed=3)
    assert len(greedy["actions"]) != len(noisy["actions"]) or not np.array_equal(
        greedy["obs"], noisy["obs"])


def test_cloning_learns_far_above_random_guessing():
    train = generate_dataset(num_games=400, eps=0.2, seed=0)
    val = generate_dataset(num_games=60, eps=0.2, seed=1)
    chance = float(np.mean(1.0 / val["masks"].sum(axis=1)))
    model, history = train_bc(train, val, epochs=3, batch_size=256, lr=1e-3, seed=0,
                              log=lambda *_: None)
    agreement = _accuracy(model.policy, val)["overall"]
    assert agreement > chance + 0.15
    assert history[-1]["train_loss"] < history[0]["train_loss"]
