"""Fast end-to-end smoke test for the training pipeline itself -- not meant to
prove the agent learns anything (that's rl/evaluate.py's job on a real run), just
that MaskablePPO + GoStopSelfPlayEnv + CheckpointPool wire together without error
as the surrounding code evolves."""

from pathlib import Path

from rl.train import train


def test_training_smoke_run_produces_a_loadable_checkpoint(tmp_path: Path):
    model, final_path = train(
        total_timesteps=64, checkpoint_dir=tmp_path, save_freq=64, eval_freq=64,
        eval_episodes=2, n_steps=64, batch_size=16, seed=0, verbose=0,
    )
    assert final_path.exists()
    assert (tmp_path / "training_log.csv").exists()

    from sb3_contrib import MaskablePPO
    reloaded = MaskablePPO.load(str(final_path))
    assert reloaded is not None
