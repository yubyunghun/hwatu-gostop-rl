from pathlib import Path

from rl.behavior_cloning import generate_dataset, train_bc
from rl.finetune import finetune


def test_finetune_smoke_seeds_the_league_and_fits_the_value_head(tmp_path: Path):
    train = generate_dataset(num_games=200, eps=0.2, seed=0)
    val = generate_dataset(num_games=20, eps=0.2, seed=1)
    model, _ = train_bc(train, val, epochs=1, batch_size=256, lr=1e-3, seed=0, log=lambda *_: None)
    bc_path = tmp_path / "bc.zip"
    model.save(str(bc_path))

    out = tmp_path / "ft"
    _, final_path, warm = finetune(
        bc_path, total_timesteps=2048, checkpoint_dir=out, value_warmup_steps=3000,
        save_freq=2048, eval_freq=2048, eval_episodes=2, seed=0, verbose=0,
    )
    assert (out / "ckpt_00000000.zip").exists()  # the cloned policy is league member #0
    assert final_path.exists()
    assert (out / "training_log.csv").exists()
    # The value head starts random; warming it up on returns must actually reduce its error.
    assert warm["mse_after"] < warm["mse_before"]
