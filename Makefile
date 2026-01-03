
.PHONY: docs

docs:
	rm -r ./docs/source -f
	rm -r ./docs/_templates -f
	rm -r ./docs/_build -f
	sphinx-apidoc --private -o ./docs/source ./a_sync

cython:
	python setup.py build_ext --inplace

stubs:
	stubgen ./a_sync -o . --include-docstrings

# Update the TaskStart hook submodule and commit the change
hooks:
	mkdir -p .clinerules/hooks/submodules
	# TaskStart hook update
	if [ -d .clinerules/hooks/submodules/TaskStart ]; then \
		if [ ! -f .clinerules/hooks/submodules/TaskStart/.git ] || ! grep -q "TaskStart" .gitmodules 2>/dev/null; then \
			rm -rf .clinerules/hooks/submodules/TaskStart; \
		fi \
	fi
	if [ ! -d .clinerules/hooks/submodules/TaskStart ]; then \
		rm -rf .git/modules/clinerules/hooks/submodules/TaskStart; \
		git submodule add --force https://github.com/BobTheBuidler/TaskStart.git .clinerules/hooks/submodules/TaskStart || true; \
		test -f .gitmodules && git add .gitmodules; \
		git add .clinerules/hooks/submodules/TaskStart; \
	fi
	git submodule update --init --recursive
	git -c protocol.file.allow=always submodule update --remote .clinerules/hooks/submodules/TaskStart
	cp .clinerules/hooks/submodules/TaskStart/TaskStart .clinerules/hooks/TaskStart
	git add .clinerules/hooks/submodules/TaskStart
	git add .clinerules/hooks/TaskStart
	if ! git diff --cached --quiet; then \
		git commit -m "Update TaskStart hook submodule and file"; \
	fi
	# PostToolUse hook update
	if [ -d .clinerules/hooks/submodules/PostToolUse ]; then \
		if [ ! -f .clinerules/hooks/submodules/PostToolUse/.git ] || ! grep -q "PostToolUse" .gitmodules 2>/dev/null; then \
			rm -rf .clinerules/hooks/submodules/PostToolUse; \
		fi \
	fi
	if [ ! -d .clinerules/hooks/submodules/PostToolUse ]; then \
		rm -rf .git/modules/clinerules/hooks/submodules/PostToolUse; \
		git submodule add --force https://github.com/BobTheBuidler/PostToolUse.git .clinerules/hooks/submodules/PostToolUse || true; \
		test -f .gitmodules && git add .gitmodules; \
		git add .clinerules/hooks/submodules/PostToolUse; \
	fi
	git submodule update --init --recursive
	git -c protocol.file.allow=always submodule update --remote .clinerules/hooks/submodules/PostToolUse
	cp .clinerules/hooks/submodules/PostToolUse/PostToolUse .clinerules/hooks/PostToolUse
	chmod +x .clinerules/hooks/PostToolUse
	git add .clinerules/hooks/submodules/PostToolUse
	git add .clinerules/hooks/PostToolUse
	if ! git diff --cached --quiet; then \
		git commit -m "Update PostToolUse hook submodule and file"; \
	fi
