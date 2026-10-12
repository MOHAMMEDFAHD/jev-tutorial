# How to apply this update

1. Copy everything in this folder into your `jev-course` folder and choose **Replace** for existing files.
   Your `.venv`, `.env` and any other folders of yours are not touched.
2. Delete these old files, which this update replaces:
   - the whole `course-materials` folder (the slides now live in `modules/01-introduction-and-resources/materials/`)
   - `docs/learning-resources.md` (the current version is in `modules/01-introduction-and-resources/`)
3. In the VS Code terminal, from the `jev-course` folder:

       .\.venv\Scripts\Activate.ps1
       pip install -e ".[dev,ui]"
       pytest -q                         # expect: 98 passed, 1 skipped
       streamlit run ui/jev_playground.py

4. Save it to GitHub:

       git add -A
       git commit -m "Add Jev playground; use 31-page deck"
       git push
