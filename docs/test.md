# Playwright Test Skill — Testing Strategy

## Bottom Line

Unit tests cover CLI argument validation and command routing without requiring a live CDP connection. Integration tests that connect to a real CDP endpoint are optional and marked separately.

## Test Tiers

| Tier | Name | External Dependencies | CI | Trigger |
|------|------|----------------------|----|---------|
| 1 | Unit | None | Yes | `pytest tests/ -v` |
| 2 | Integration | CDP Chrome on port 9222 | No | Manual: start Chrome, then `pytest tests/ -v -m integration` |

## Unit Test Coverage

- `test_no_args_prints_usage_and_returns_1`: empty argv prints usage, exit 1
- `test_unknown_command_returns_1`: unknown command fails
- `test_cdp_url_default`: default CDP URL is `http://localhost:9222`
- `test_usage_contains_all_commands`: USAGE string lists all commands
- `test_goto_requires_url`: goto without URL arg fails
- `test_click_requires_selector`: click without selector fails
- `test_fill_requires_two_args`: fill without selector+value fails
- `test_wait_requires_duration`: wait without ms fails
- `test_eval_requires_expression`: eval without JS fails
- `test_screenshot_requires_path`: screenshot without path fails

## Integration Test Coverage (future)

When a CDP Chrome instance is running on port 9222:
- `goto` navigates and prints URL+title
- `snapshot` prints page state with inputs/buttons/links
- `click` clicks a visible element
- `fill` fills a visible input
- `eval` evaluates JS and prints result
- `screenshot` saves a PNG file