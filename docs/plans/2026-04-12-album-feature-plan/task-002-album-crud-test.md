# Task 002: Album CRUD — Tests

**type**: test
**depends-on**: [001]

## Goal

Write unit tests for album CRUD operations in the repository and service layers. Tests use real SQLite (in-memory) following the project's existing test patterns.

## BDD Scenarios

```gherkin
Scenario: Create a manual album
  Given the system has no albums
  When I create an album with name "Vacation 2025" and type "manual"
  Then the album is created with id > 0
  And the album type is "manual"
  And the album rule_logic is null
  And the album image_count is 0

Scenario: Create a smart album with AND logic
  Given the system has tags "sunset", "beach", "mountain"
  When I create an album with name "Beach Sunsets" and type "smart" and rule_logic "and"
  Then the album is created with type "smart" and rule_logic "and"

Scenario: Create a smart album with OR logic
  Given the system has tags "cat", "dog"
  When I create an album with name "Pets" and type "smart" and rule_logic "or"
  Then the album is created with type "smart" and rule_logic "or"

Scenario: Album name must be unique
  Given an album named "My Album" exists
  When I create an album with name "My Album"
  Then the operation fails with an integrity error

Scenario: Album name must not be empty
  When I create an album with name ""
  Then the operation raises ValueError

Scenario: Update album name and description
  Given an album named "Old Name" exists
  When I update the album name to "New Name" and description to "Updated"
  Then the album name is "New Name"
  And the album description is "Updated"
  And the album updated_at is newer than created_at

Scenario: Delete album does not delete images
  Given a manual album "Travel" with 3 images
  When I delete the album "Travel"
  Then the album no longer exists
  And all 3 images still exist in the images table

Scenario: Get non-existent album returns None
  When I request album with id 9999
  Then the result is None
```

## Files to Create

- `tests/unit/test_album_service.py` — Test class for album CRUD (create, list, get, update, delete)

## What to Test

Write test functions for each BDD scenario above. Use the existing test pattern from `tests/unit/test_tag_service.py`:
- Create a `MetadataRepository` with in-memory SQLite
- Initialize schema
- Create `AlbumService` with the repository
- Each test method exercises one scenario

Helper: Create a fixture or setup method that initializes the repository with sample images (needed for album_images FK constraints).

## Verification

```bash
pytest tests/unit/test_album_service.py -v
# All tests should FAIL (Red) since repository methods don't exist yet
```
