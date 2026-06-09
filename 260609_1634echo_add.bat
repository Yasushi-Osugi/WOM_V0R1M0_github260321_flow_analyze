echo "pytest-cache-files-*/" >> "WOM v1r0m0/.gitignore"
echo ".pytest_cache/" >> "WOM v1r0m0/.gitignore"
echo "__pycache__/" >> "WOM v1r0m0/.gitignore"
echo "*.pyc" >> "WOM v1r0m0/.gitignore"
echo "output/" >> "WOM v1r0m0/.gitignore"

git add "WOM v1r0m0/.gitignore"
git commit -m "chore: add .gitignore for WOM v1r0m0"
git push wom_v1r0m0 HEAD:main