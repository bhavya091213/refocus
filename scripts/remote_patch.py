"""Idempotent patches to the authors' code on the training machine. Every change is documented in the report.
 1. svd_runner: stream training loss to the dashboard (DASH_URL env) every 20 steps.
 2. utils.FocalStackDataset: optional fixed test subset via REFOCUS_EVAL_SCENES / REFOCUS_EVAL_POS (env), and a correct scene index when fewer than 9 positions are used.
 (3. svd_runner: REFOCUS_SKIP_VAL and validation.py: REFOCUS_MAX_ITEMS were added earlier.)"""
import io, os

R = os.path.expanduser("~/refocus/learn2refocus/training/")


def patch(path, old, new, tag):
    s = io.open(R + path, encoding="utf-8", newline="").read()
    if tag in s:
        print("already:", tag); return
    if "\r\n" in s:  # the authors' files may use CRLF; keep each file's own line endings
        old, new = old.replace("\n", "\r\n"), new.replace("\n", "\r\n")
    assert old in s, f"anchor not found for {tag}"
    io.open(R + path, "w", encoding="utf-8", newline="").write(s.replace(old, new, 1)); print("patched:", tag)


# 1 ---- loss streaming
patch("svd_runner.py",
      "                    accelerator.log({\"train_loss\": train_loss}, step=global_step)\n                    train_loss = 0.0\n",
      "                    accelerator.log({\"train_loss\": train_loss}, step=global_step)\n"
      "                    if accelerator.is_main_process and global_step % 20 == 0 and os.environ.get('DASH_URL'):  # REFOCUS_DASH_PATCH\n"
      "                        try:\n"
      "                            import json as _j, urllib.request as _u\n"
      "                            _u.urlopen(_u.Request(os.environ['DASH_URL'] + '/api/ingest/metric?key=' + os.environ['DASH_KEY'], data=_j.dumps({'run': args.run_name, 'step': global_step, 'loss': float(train_loss), 'lr': float(lr_scheduler.get_last_lr()[0])}).encode(), headers={'Content-Type': 'application/json'}), timeout=3).read()\n"
      "                        except Exception:\n"
      "                            pass\n"
      "                    train_loss = 0.0\n",
      "REFOCUS_DASH_PATCH")

# 2 ---- fixed eval subset
patch("utils.py",
      "        if split == \"test\":\n            self.scenes = [(scene, idx) for scene in self.scenes for idx in range(self.sample_frames)]\n",
      "        if split == \"test\":  # REFOCUS_EVAL_PATCH\n"
      "            _n = int(os.environ.get('REFOCUS_EVAL_SCENES', 0))\n"
      "            _pos = [int(x) for x in os.environ.get('REFOCUS_EVAL_POS', ','.join(str(i) for i in range(self.sample_frames))).split(',')]\n"
      "            if _n: self.scenes = self.scenes[::max(1, len(self.scenes) // _n)][:_n]\n"
      "            self._npos = len(_pos)\n"
      "            self.scenes = [(scene, idx) for scene in self.scenes for idx in _pos]\n",
      "REFOCUS_EVAL_PATCH")
patch("utils.py", "            out_dict[\"idx\"] = idx//9\n", "            out_dict[\"idx\"] = idx//getattr(self, '_npos', 9)  # REFOCUS_IDX_PATCH\n", "REFOCUS_IDX_PATCH")

# 3 ---- skip the authors' in-training validation (crashes under bf16; we evaluate separately)
patch("svd_runner.py", "if args.test or (global_step % args.validation_steps == 0) or (global_step == 1):",
      "if args.test or (not os.environ.get('REFOCUS_SKIP_VAL') and ((global_step % args.validation_steps == 0) or (global_step == 1))):  # REFOCUS_SKIP_VAL", "REFOCUS_SKIP_VAL")
