# Task 003: Manual Album Image Management — Tests

**type**: test
**depends-on**: [001]

## Goal

Write unit tests for manual album image add/remove/list operations.

## BDD Scenarios

```gherkin
Scenario: Add images to manual album
  Given a manual album "Favorites" exists
  And 3 indexed images exist
  When I add all 3 images to "Favorites"
  Then the album image_count is 3

Scenario: Image can belong to multiple albums
  Given manual albums "Album A" and "Album B" exist
  And an indexed image with hash "abc123" exists
  When I add "abc123" to "Album A"
  And I add "abc123" to "Album B"
  Then "Album A" contains "abc123"
  And "Album B" contains "abc123"

Scenario: Remove image from manual album
  Given a manual album "Favorites" with image "abc123"
  When I remove "abc123" from "Favorites"
  Then the album image_count is 0
  And image "abc123" still exists in the images table

Scenario: Cannot add images to smart album
  Given a smart album "Auto Pets" exists
  When I try to add image "abc123" to "Auto Pets"
  Then the operation raises ValueError

Scenario: Adding duplicate image is idempotent
  Given a manual album "Favorites" with image "abc123"
  When I add "abc123" to "Favorites" again
  Then no error occurs
  And the album image_count is still 1

Scenario: Bulk add images to album
  Given a manual album "Batch" exists
  And 10 indexed images exist
  When I add all 10 images to "Batch" in a single request
  Then the album image_count is 10

Scenario: Paginate album images with cursor
  Given a manual album "Large" with 25 images
  When I request album images with limit 10
  Then I receive 10 images and a next_cursor
  When I request album images with limit 10 and cursor = next_cursor
  Then I receive 10 more images and a next_cursor
  When I request album images with the second cursor
  Then I receive 5 images and next_cursor is null

Scenario: Cannot remove images from smart album
  Given a smart album "Auto" exists
  When I try to remove image "abc123" from "Auto"
  Then the operation raises ValueError

Scenario: Bulk add exceeding limit returns error
  Given a manual album "Test" exists
  When I try to add 501 images to "Test"
  Then the operation raises ValueError
```

## Files to Create

- `tests/unit/test_album_service.py` — Add test methods for image management (append to file from task 002)

## What to Test

Test functions for each BDD scenario. Use helper methods to create sample images in the database (INSERT into images table with required fields).

## Verification

```bash
pytest tests/unit/test_album_service.py -v -k "image"
# All image management tests should FAIL (Red)
```
