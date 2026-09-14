"""Queue runner for the Yosys + OpenSTA configurations (Y, O0-O2, Ycoevo):  python -m src.eval.run_yosys --job <job_id>
Same payload and exit codes as src.eval.run_dc (the evaluation service dispatches on the configuration's tool); kept as
its own module so that the `yosys` job kind (local pool, no DC seat) has a runner."""
import sys

from src.eval.run_dc import main

if __name__ == "__main__":
    sys.exit(main())
