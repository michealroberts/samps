# Contributing

Thank you for your interest in contributing to **samps**! 

We welcome well-considered contributions that adhere to the following guidelines.

## Be Nice

We are a friendly community and we expect all contributors to be respectful and considerate. Please be kind to each other, and remember that everyone is here to learn and grow. We welcome robust discussions, but please keep them constructive and focused on the code.

Anyone who violates this code of conduct may be disqualified from contributing to the repository.

## Workflow & Communication

1. Review the existing [issues](https://github.com/michealroberts/samps/issues) and [pull requests](https://github.com/michealroberts/samps/pulls) to confirm that your contribution is not a duplicate.

2. If you have identified a bug or wish to propose a feature, create a new issue using the appropriate template:

   * **Bug Report**: `.github/ISSUE_TEMPLATE/bug.md`
   * **Feature Request**: `.github/ISSUE_TEMPLATE/feature.md`

3. Engage in discussion until there is consensus on the scope and design of your contribution.

4. If you have a question or need clarification, please use the [Discussions](https://github.com/michealroberts/samps/discussions) section of the repository. This is the best place to ask questions, share ideas, and discuss potential changes with the community before starting work on a new feature or bug fix.

5. If you are unsure about the design or implementation of your contribution, please open a discussion thread to seek feedback before proceeding with a pull request.

6. If you are working on a large change, consider breaking it into smaller, more manageable pull requests. This will make it easier for maintainers to review and merge your changes.

## Branching & Development

1. Fork the repository:

   * Go to the repository on GitHub.
   * Click the "Fork" button in the upper right corner.
   * This creates a copy of the repository under your GitHub account.

2. Clone your fork locally:

   ```bash
   git clone https://github.com/<YOUR_USERNAME>/samps.git
   cd samps
   ```
3. Create a feature branch named according to the change:

   * `fix/<TOPIC>/<SHORT-DESCRIPTION>` for bug fixes
   * `feature/<TOPIC>/<SHORT-DESCRIPTION>` for new features
   * `docs/<TOPIC>/<SHORT-DESCRIPTION>` for documentation updates

  where the topic is the area of the codebase affected (e.g. `serial`, `tcp`) and the short description is a brief summary of the change.

4. Implement your changes. Ensure that all code additions and modifications:

   * Conform to the existing code style and formatting.
   * Maintain zero external dependencies.
   * Include adequate type annotations and docstrings.

5. Add tests for new behavior or to reproduce identified bugs.

6. Update documentation (e.g. `README.md`, docstrings) to reflect any changes (if applicable).

## 3. Commit Standards

All commits must be:

* **Atomic**: each commit should implement a single logical change.
* **Semantic**: use [Conventional Commits](https://www.conventionalcommits.org/) of the form:

  ```
  <type>(<scope>): <subject>

  <body>            # optional detailed description

  <footer>          # optional metadata, e.g., Closes #123
  ```

  * **type**: one of `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`.
  * **scope**: the area of the codebase affected (e.g. `serial`, `tcp`).
  * **subject**: brief imperative description (< 72 characters).
  * **body**: more detailed explanation of what and why (wrap at 72 characters).
  * **footer**: reference issues or indicate breaking changes (`BREAKING CHANGE:`).
  * **breaking change**: if your commit introduces a breaking change, add `!` after the type and before the colon in the subject line.
  * **metadata**: if your commit closes an issue, add `Closes #<issue-number>` in the footer.

Examples:

```
feat(rfc2217): add support for RFC2217 URL parsing
fix(serial): handle empty-read timeout correctly
```

## 4. Testing & Validation

All of the following steps will be performed by the CI/CD pipelines in place for this repository, but it is a good idea to run them locally before submitting your pull request.

1. Add or update tests to cover your changes.

2. Ensure all existing tests pass as well as your new tests:

```bash
uv run --link-mode=copy pytest test
```

3. Run the linter to check for code style issues:

```bash
uv run ruff check
```

```bash
uv run ruff format
```

4. Run the type checker to ensure type safety:

```bash
uv run mypy ./src/samps --config mypy.ini
```

## 5. Pull Request Submission

1. Push your branch to your fork:

   ```bash
   git push origin <branch-name>
   ```
2. Open a pull request against the repository’s `main` branch.
3. In the pull request description, reference related issues, summarize changes, and note any backward-incompatible alterations.
4. Respond to maintainers’ feedback promptly and update your branch as required.

## 6. Versioning

This project follows [Semantic Versioning](https://semver.org/):

* **MAJOR** version when you make incompatible API changes,
* **MINOR** version when you add functionality in a backward-compatible manner,
* **PATCH** version when you make backward-compatible bug fixes.

Label breaking changes clearly in commit messages and pull requests with the `!` symbol, e.g., `fix()!: `.

---

We appreciate your contributions to **samps**. For any questions not covered here, please refer to the project’s Discussions page.
