# Design Document

## Overview

This design implements a GitHub Actions CI/CD pipeline that automates testing, building, and publishing the derpy-tool Python package to PyPI. The pipeline uses a single workflow file that handles both pull request validation and production deployment, with conditional logic to determine which stages to execute based on the trigger event.

The workflow follows industry best practices for Python package publishing, including:

- Isolated test execution in virtual environments
- Multi-stage pipeline with clear separation of concerns (test → build → publish)
- Secure credential management using GitHub Environments
- Trusted publishing via PyPI API tokens
- Automated package distribution to PyPI on main branch merges

## Architecture

### Workflow Trigger Strategy

The workflow uses GitHub Actions event-based triggers:

1. **Pull Request Events**: Triggers on `pull_request` targeting the `main` branch

   - Executes: Test stage only
   - Purpose: Validate code quality before merge

2. **Push Events**: Triggers on `push` to the `main` branch
   - Executes: Test → Build → Publish stages
   - Purpose: Deploy verified code to PyPI

### Pipeline Stages

```
┌─────────────────────────────────────────────────────────────┐
│                     GitHub Actions Workflow                  │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Stage 1: Test                                               │
│  ┌────────────────────────────────────────────────────┐     │
│  │ • Setup Python 3.8, 3.9, 3.10, 3.11, 3.12         │     │
│  │ • Install dependencies (including dev)             │     │
│  │ • Run pytest with coverage                         │     │
│  │ • Fail fast if any test fails                      │     │
│  └────────────────────────────────────────────────────┘     │
│                          ↓                                    │
│  Stage 2: Build (only on push to main)                       │
│  ┌────────────────────────────────────────────────────┐     │
│  │ • Setup Python 3.11                                │     │
│  │ • Install build tools (build package)              │     │
│  │ • Build wheel and source distribution              │     │
│  │ • Upload artifacts for publish stage               │     │
│  └────────────────────────────────────────────────────┘     │
│                          ↓                                    │
│  Stage 3: Publish (only on push to main)                     │
│  ┌────────────────────────────────────────────────────┐     │
│  │ • Download build artifacts                         │     │
│  │ • Use pypi environment for credentials             │     │
│  │ • Publish to PyPI using pypa/gh-action-pypi-publish│     │
│  └────────────────────────────────────────────────────┘     │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Job Dependencies

```
test (matrix: Python 3.8-3.12)
  ↓
build (needs: test, if: push to main)
  ↓
publish (needs: build, if: push to main, environment: pypi)
```

## Components and Interfaces

### 1. Workflow File Structure

**Location**: `.github/workflows/ci-cd.yaml`

**Key Components**:

- `name`: Workflow display name
- `on`: Event triggers (pull_request, push)
- `jobs`: Test, build, and publish jobs
- `permissions`: Required GitHub token permissions

### 2. Test Job

**Purpose**: Validate code quality across multiple Python versions

**Configuration**:

- **Runs-on**: `ubuntu-latest`
- **Strategy**: Matrix testing across Python 3.8, 3.9, 3.10, 3.11, 3.12
- **Steps**:
  1. Checkout code (`actions/checkout@v4`)
  2. Setup Python (`actions/setup-python@v5`)
  3. Install dependencies: `pip install -e ".[dev]"`
  4. Run tests: `pytest`

**Exit Criteria**: All tests must pass for all Python versions

### 3. Build Job

**Purpose**: Create distributable Python package

**Configuration**:

- **Runs-on**: `ubuntu-latest`
- **Needs**: `test` job must complete successfully
- **Condition**: Only runs on push to main branch
- **Steps**:
  1. Checkout code
  2. Setup Python 3.11
  3. Install build tools: `pip install build`
  4. Build package: `python -m build`
  5. Upload artifacts: `actions/upload-artifact@v4`

**Outputs**:

- Wheel file: `derpy_tool-*.whl`
- Source distribution: `derpy-tool-*.tar.gz`

### 4. Publish Job

**Purpose**: Upload package to PyPI

**Configuration**:

- **Runs-on**: `ubuntu-latest`
- **Needs**: `build` job must complete successfully
- **Condition**: Only runs on push to main branch
- **Environment**: `pypi` (GitHub Environment for credential management)
- **Permissions**: `id-token: write` (for trusted publishing)
- **Steps**:
  1. Download build artifacts: `actions/download-artifact@v4`
  2. Publish to PyPI: `pypa/gh-action-pypi-publish@release/v1`

**Authentication**: Uses PyPI API token stored in GitHub Environment secrets

## Data Models

### GitHub Actions Context

```yaml
Event Context:
  - github.event_name: "pull_request" | "push"
  - github.ref: Branch reference
  - github.repository: Repository name

Job Context:
  - needs.<job>.result: "success" | "failure" | "cancelled"
  - matrix.python-version: Python version for current job
```

### Artifacts

```
Build Artifacts:
  Name: "python-package-distributions"
  Path: "dist/"
  Contents:
    - derpy_tool-0.1.0-py3-none-any.whl
    - derpy-tool-0.1.0.tar.gz
  Retention: 90 days (GitHub default)
```

### Environment Variables

```yaml
GitHub Secrets (in pypi environment):
  - PYPI_API_TOKEN: PyPI authentication token
    OR
  - Trusted Publisher configuration (recommended)
```

## Package Name Configuration

The package name must be changed from "derpy" to "derpy-tool" in `pyproject.toml`:

```toml
[project]
name = "derpy-tool"  # Changed from "derpy"
```

This ensures the package is published to PyPI as "derpy-tool" while maintaining the import name as `derpy`.

## Error Handling

### Test Failures

**Scenario**: One or more tests fail during the test job

**Behavior**:

- Job exits with non-zero status code
- Workflow marked as failed
- Build and publish jobs are skipped
- GitHub provides detailed test output in job logs

**User Action**: Fix failing tests and push changes

### Build Failures

**Scenario**: Package build fails (e.g., missing files, invalid configuration)

**Behavior**:

- Build job exits with error
- Publish job is skipped
- Workflow marked as failed

**User Action**: Review build logs, fix configuration issues

### Publish Failures

**Scenario**: PyPI upload fails (e.g., authentication error, duplicate version)

**Behavior**:

- Publish job exits with error
- Workflow marked as failed
- Package remains unpublished

**Common Causes**:

1. Missing or invalid PyPI API token
2. Version already exists on PyPI
3. Package name conflicts
4. PyPI service unavailable

**User Action**:

- Verify GitHub Environment "pypi" is configured
- Check PyPI API token is valid
- Increment version number if duplicate
- Review PyPI upload logs

### Conditional Execution Safeguards

**Scenario**: Accidental trigger or misconfiguration

**Safeguards**:

1. Build only runs on push to main (not PRs)
2. Publish only runs on push to main (not PRs)
3. Publish requires successful build
4. Publish requires pypi environment approval (if configured)

## Testing Strategy

### Pre-Deployment Testing

**Local Workflow Validation**:

```bash
# Validate workflow syntax
gh workflow view ci-cd.yaml

# Test workflow locally (if using act)
act pull_request
```

**Branch Testing**:

1. Create feature/ci-cd branch
2. Push workflow file
3. Create draft PR to main
4. Verify test job runs successfully
5. Verify build/publish jobs are skipped (PR context)

### Post-Deployment Testing

**Pull Request Flow**:

1. Create test PR to main
2. Verify workflow triggers
3. Verify all Python versions tested
4. Verify build/publish skipped
5. Merge PR

**Main Branch Flow**:

1. Merge PR to main
2. Verify workflow triggers
3. Verify tests pass
4. Verify package builds
5. Verify package publishes to PyPI
6. Verify package installable: `pip install derpy-tool`

### Rollback Strategy

**If deployment fails**:

1. Workflow failure does not affect existing PyPI package
2. Fix issues in new PR
3. Merge fix to trigger new deployment

**If bad package published**:

1. Cannot delete PyPI versions (PyPI policy)
2. Publish new patch version with fixes
3. Yank bad version on PyPI (marks as unavailable)

## GitHub Environment Setup

### Creating the PyPI Environment

**Manual Setup Required** (by user after workflow creation):

1. Navigate to GitHub repository → Settings → Environments
2. Create new environment named "pypi"
3. Configure environment protection rules (optional):
   - Required reviewers
   - Wait timer
   - Deployment branches (main only)
4. Add environment secret:
   - Name: `PYPI_API_TOKEN`
   - Value: PyPI API token from https://pypi.org/manage/account/token/

### Alternative: Trusted Publishing (Recommended)

PyPI supports trusted publishing without API tokens:

1. Configure on PyPI:
   - Go to PyPI project settings
   - Add GitHub as trusted publisher
   - Specify: owner, repository, workflow name, environment
2. Remove `PYPI_API_TOKEN` from GitHub
3. Workflow uses OIDC token automatically

## Workflow Optimization

### Caching Strategy

**Python Dependencies**:

```yaml
- uses: actions/setup-python@v5
  with:
    python-version: ${{ matrix.python-version }}
    cache: "pip"
```

**Benefits**:

- Faster workflow execution
- Reduced network usage
- Consistent dependency versions

### Matrix Strategy

**Python Version Testing**:

- Tests run in parallel across all Python versions
- Fail-fast disabled to see all version results
- Provides confidence in cross-version compatibility

### Artifact Management

**Build Artifacts**:

- Uploaded after build job
- Downloaded in publish job
- Automatically cleaned up after 90 days
- Enables build/publish separation

## Security Considerations

### Credential Management

1. **Never commit API tokens**: Use GitHub Secrets only
2. **Environment protection**: Use GitHub Environments for deployment gates
3. **Minimal permissions**: Workflow uses least-privilege permissions
4. **Token scope**: PyPI token scoped to derpy-tool project only

### Workflow Permissions

```yaml
permissions:
  contents: read # Read repository contents
  id-token: write # Write OIDC tokens (for trusted publishing)
```

### Branch Protection

**Recommended Settings** (manual configuration):

1. Require PR reviews before merge
2. Require status checks (CI/CD workflow)
3. Require branches to be up to date
4. Restrict push to main branch

## Maintenance and Monitoring

### Workflow Monitoring

**GitHub Actions Dashboard**:

- View workflow runs
- Check job status
- Review logs
- Download artifacts

**Notifications**:

- GitHub sends email on workflow failure
- Configure Slack/Discord webhooks (optional)

### Version Management

**Updating Package Version**:

1. Update version in `pyproject.toml`
2. Commit and push to feature branch
3. Create PR to main
4. Merge PR → automatic PyPI publish

**Version Strategy**:

- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Current: 0.1.0 (alpha)
- Next: 0.1.1 (patch), 0.2.0 (minor), 1.0.0 (major)

### Workflow Updates

**Updating Actions Versions**:

- Dependabot can automate action updates
- Review changelogs before updating
- Test in feature branch before merging

**Adding New Jobs**:

- Add to jobs section
- Configure dependencies with `needs`
- Test thoroughly before production use
