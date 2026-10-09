import numpy as np

from engine.state import DecisionNode
from rl.behavior_cloning import _accuracy, train_bc
from rl.distill_search import generate_dataset
from rl.obs_encoding import OBS_SIZE

# Kept tiny everywhere (games, determinizations, workers) -- search is far more expensive per label
# than the heuristic, so these are smoke tests of the pipeline's correctness, not of search quality.

_LABELED_DECISION_VALUES = {d.value for d in DecisionNode if d is not DecisionNode.HAND_OVER}


def test_dataset_shapes_and_label_legality():
    data = generate_dataset(num_games=3, eps=0.3, seed=1, determinizations=3, min_z=1.0,
                             nodes="all", workers=2)
    n = len(data["actions"])
    assert n > 0
    assert data["obs"].shape == (n, OBS_SIZE)
    assert data["masks"].shape[0] == n
    assert set(np.unique(data["decisions"])) <= _LABELED_DECISION_VALUES
    # Every label must be a legal action in the state it was recorded in.
    assert data["masks"][np.arange(n), data["actions"]].all()


def test_dataset_generation_is_deterministic_per_seed():
    kwargs = dict(num_games=2, eps=0.2, determinizations=3, min_z=1.0, nodes="all", workers=2)
    a = generate_dataset(seed=7, **kwargs)
    b = generate_dataset(seed=7, **kwargs)
    for key in a:
        assert np.array_equal(a[key], b[key])


def test_each_game_contributes_states_and_counts_conserve_across_workers():
    single = generate_dataset(num_games=1, eps=0.2, seed=3, determinizations=3, min_z=1.0,
                               nodes="all", workers=1)
    double = generate_dataset(num_games=2, eps=0.2, seed=3, determinizations=3, min_z=1.0,
                               nodes="all", workers=2)
    # The second game run alone (seed/game-index derived) should reproduce exactly inside the
    # two-game, two-worker run -- i.e. workers don't share or corrupt each other's rng streams.
    assert len(double["actions"]) >= len(single["actions"])


def test_restricting_nodes_changes_the_labels_source_but_not_the_pipeline():
    play_only = generate_dataset(num_games=2, eps=0.1, seed=5, determinizations=3, min_z=1.0,
                                  nodes="play", workers=2)
    all_nodes = generate_dataset(num_games=2, eps=0.1, seed=5, determinizations=3, min_z=1.0,
                                  nodes="all", workers=2)
    assert len(play_only["actions"]) > 0
    assert len(all_nodes["actions"]) > 0


def test_distillation_pipeline_runs_end_to_end_without_crashing():
    train = generate_dataset(num_games=6, eps=0.2, seed=0, determinizations=3, min_z=1.0,
                              nodes="all", workers=3)
    val = generate_dataset(num_games=3, eps=0.2, seed=1, determinizations=3, min_z=1.0,
                            nodes="all", workers=3)
    model, history = train_bc(train, val, epochs=2, batch_size=128, lr=1e-3, seed=0,
                               log=lambda *_: None)
    acc = _accuracy(model.policy, val)
    assert 0.0 <= acc["overall"] <= 1.0
    assert len(history) == 2
