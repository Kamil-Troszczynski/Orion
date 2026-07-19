from dotenv import load_dotenv

load_dotenv()

from src.pipeline import *


if __name__ == "__main__":
    from pipecat.runner.run import main
    main()