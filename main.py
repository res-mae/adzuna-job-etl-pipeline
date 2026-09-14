from src.extract import run_extract
from src.transform import run_transform
from src.load import run_load

def main():
    if not run_extract():
        print("Extraction failed - stopping pipeline.")
        return

    if not run_transform():
        print("Transform failed - stopping pipeline.")
        return
    
    if not run_load():
        print("Load failed.")
        return

    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()