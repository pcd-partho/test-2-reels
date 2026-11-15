# Auto Video Pipeline

Makes a short animated video (9:16) about a trending GitHub repo, in Bangla, Hindi or English,
and sends the video, thumbnail and caption to your Telegram.

- Edit `config.yaml` to change language rotation, length and models.
- Add royalty-free music files (mp3) to `assets/music/` (optional).
- Run by hand: Actions tab > make-video > Run workflow.
- Test without internet or keys: `DRY_RUN=1 python -m pipeline.run`
- The workflow runs Mon, Wed, Fri at 03:00 UTC. Edit `.github/workflows/daily.yml` to change.
