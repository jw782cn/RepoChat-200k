import argparse
import logging
from utils.utils import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main(repo_url):
    local_path = "./repos"
    repo_path = clone_repo(repo_url, local_path)
    if repo_path:
        logger.info(f"Repository downloaded to: {repo_path}")
    else:
        logger.error("Failed to download the repository.")
        return

    repo_name = repo_url.split('/')[-1]
    extracted_repo_path = os.path.join(repo_path, f"{repo_name}-main")

    csv_path = os.path.join(repo_path, "repo_stats.csv")
    df, csv_path = repo_stats(extracted_repo_path, csv_path)
    logger.info(f"Repository stats saved to: {csv_path}")
    
    # if you want to extract some meta data, you can refer to `metadata_extract.py`

    language_percent = language_percentage(csv_path)
    if language_percent is not None:
        logger.info("Language percentage:")
        for lang, percent in language_percent.items():
            logger.info(f"{lang}: {percent:.2f}%")
    else:
        logger.warning("Failed to calculate language percentage.")

    logger.info("Repository directory structure:")
    print_directory_structure(extracted_repo_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Download and analyze a GitHub repository.')
    parser.add_argument('repo_url', type=str, help='GitHub repository URL')
    args = parser.parse_args()

    main(args.repo_url)