# Task 004: Smart Album Rules and Query — Tests

**type**: test
**depends-on**: [001]

## Goal

Write unit tests for smart album rule management and the real-time image matching query with AND/OR/exclude logic and source path filtering.

## BDD Scenarios

```gherkin
Scenario: AND logic — all included tags required
  Given tags "sunset" and "beach" exist
  And image "img1" has tags ["sunset", "beach"]
  And image "img2" has tags ["sunset"]
  And image "img3" has tags ["beach"]
  And a smart album "Beach Sunsets" with rule_logic "and" and rules: include "sunset", include "beach"
  When I list images in "Beach Sunsets"
  Then only "img1" is returned

Scenario: OR logic — any included tag matches
  Given tags "cat" and "dog" exist
  And image "img1" has tags ["cat"]
  And image "img2" has tags ["dog"]
  And image "img3" has tags ["mountain"]
  And a smart album "Pets" with rule_logic "or" and rules: include "cat", include "dog"
  When I list images in "Pets"
  Then "img1" and "img2" are returned
  And "img3" is not returned

Scenario: Exclude tag filters out matching images
  Given tags "landscape", "urban" exist
  And image "img1" has tags ["landscape"]
  And image "img2" has tags ["landscape", "urban"]
  And a smart album with rule_logic "or", rules: include "landscape", exclude "urban"
  When I list images in the album
  Then only "img1" is returned

Scenario: AND with exclude — must have all includes, none of excludes
  Given tags "food", "dessert", "savory" exist
  And image "img1" has tags ["food", "dessert"]
  And image "img2" has tags ["food", "savory"]
  And image "img3" has tags ["food", "dessert", "savory"]
  And a smart album with rule_logic "and", rules: include "food", include "dessert", exclude "savory"
  When I list images in the album
  Then only "img1" is returned

Scenario: Rule changes are immediately reflected
  Given a smart album "Dynamic" with rule_logic "or" and rules: include "sunset"
  And image "img1" has tag "sunset"
  When I list images in "Dynamic"
  Then "img1" is returned
  When I add tag "beach" to "img1"
  And I update rules to: include "beach" (removing "sunset")
  And I list images in "Dynamic"
  Then "img1" is still returned (now matches via "beach")

Scenario: Deleting a tag updates smart album results
  Given a smart album with rule_logic "and", rules: include tag "sunset", include tag "beach"
  And image "img1" has tags ["sunset", "beach"]
  When tag "sunset" is deleted
  Then the rule referencing "sunset" is also deleted (CASCADE)
  And listing the album now uses only the remaining "beach" rule
  And "img1" still matches (has "beach")

Scenario: Smart album with no rules returns no images
  Given a smart album "Empty Rules" with no rules defined
  When I list images in "Empty Rules"
  Then 0 images are returned

Scenario: Smart album with no include rules returns no images
  Given tags "landscape", "urban" exist
  And images with various tags exist
  And a smart album with rule_logic "or" and rules: exclude "urban" (no include rules)
  When I list images in the album
  Then 0 images are returned

Scenario: AND album after all include tags deleted returns no images
  Given a smart album with rule_logic "and", rules: include tag "sunset"
  And image "img1" has tag "sunset"
  When tag "sunset" is deleted (CASCADE removes the rule)
  Then the album has 0 rules
  And listing images in the album returns 0 results

Scenario: set_album_rules with empty list clears all rules
  Given a smart album "Dynamic" with 3 rules
  When I set rules to an empty list
  Then the album has 0 rules
  And listing images returns 0 results

Scenario: set_album_rules with duplicate tag_id fails
  Given a smart album "Test" exists
  And tag "sunset" (id=1) exists
  When I set rules with two entries for tag_id=1
  Then the operation raises ValueError

Scenario: Paginate smart album images with cursor
  Given tags "nature" exists
  And 25 images all have tag "nature"
  And a smart album with rule_logic "or" and rules: include "nature"
  When I request album images with limit 10
  Then I receive 10 images and a next_cursor
  When I request album images with limit 10 and cursor = next_cursor
  Then I receive 10 more images and a next_cursor
  When I request album images with the second cursor
  Then I receive 5 images and next_cursor is null

Scenario: Smart album with source paths only matches images in those paths
  Given tags "sunset" exists
  And image "img1" at path "<images_root>/photos/2025/sunset.jpg" has tag "sunset"
  And image "img2" at path "<images_root>/photos/2024/sunset.jpg" has tag "sunset"
  And image "img3" at path "<images_root>/videos/sunset.jpg" has tag "sunset"
  And a smart album with rule_logic "or", rules: include "sunset", source_paths: ["photos/2025"]
  When I list images in the album
  Then only "img1" is returned

Scenario: Smart album with multiple source paths
  Given tags "landscape" exists
  And image "img1" at path "<images_root>/photos/2025/land.jpg" has tag "landscape"
  And image "img2" at path "<images_root>/photos/2024/land.jpg" has tag "landscape"
  And image "img3" at path "<images_root>/other/land.jpg" has tag "landscape"
  And a smart album with source_paths: ["photos/2025", "photos/2024"]
  When I list images in the album
  Then "img1" and "img2" are returned
  And "img3" is not returned

Scenario: Smart album with no source paths matches all images
  Given tags "nature" exists
  And images in various paths all have tag "nature"
  And a smart album with source_paths: [] (empty)
  When I list images in the album
  Then all images with tag "nature" are returned regardless of path

Scenario: Set source paths for smart album
  Given a smart album "Travel" exists
  When I set source paths to ["photos/travel", "photos/vacation"]
  Then the album has 2 source paths

Scenario: Cannot set source paths for manual album
  Given a manual album "Manual" exists
  When I try to set source paths for "Manual"
  Then the operation raises ValueError
```

## Files to Create

- `tests/unit/test_album_smart_query.py` — All smart album rule and query tests

## What to Test

Create test class with helper methods to:
- Insert images with specific canonical_paths into the images table
- Create tags and assign them to images via image_tags table
- Create smart albums with rules and source paths
- Query and verify results

## Verification

```bash
pytest tests/unit/test_album_smart_query.py -v
# All tests should FAIL (Red)
```
