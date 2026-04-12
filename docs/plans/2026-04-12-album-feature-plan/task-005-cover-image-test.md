# Task 005: Cover Image and Album Listing — Tests

**type**: test
**depends-on**: [001]

## Goal

Write unit tests for cover image selection and album listing with image counts.

## BDD Scenarios

```gherkin
Scenario: Manual album cover is first image by sort_order
  Given a manual album "Travel" with images added in order: "img1", "img2", "img3"
  When I list albums
  Then "Travel" has cover_image matching "img1"

Scenario: Smart album cover is first image in query result
  Given a smart album "Sunsets" matching images "img_a", "img_b" (ordered by canonical_path)
  When I list albums
  Then "Sunsets" has cover_image matching whichever comes first alphabetically

Scenario: Empty album has null cover
  Given a manual album "Empty" with no images
  When I list albums
  Then "Empty" has cover_image = null

Scenario: List albums shows image count and cover
  Given a manual album "A" with 5 images
  And a smart album "B" matching 3 images
  And a manual album "C" with 0 images
  When I list all albums
  Then I receive 3 albums
  And album "A" has image_count 5 and a cover_image
  And album "B" has image_count 3 and a cover_image
  And album "C" has image_count 0 and cover_image null
```

## Files to Modify

- `tests/unit/test_album_service.py` — Add test methods for cover image and listing

## What to Test

Test functions for each BDD scenario. Requires creating albums with images/rules and verifying the `list_albums()` response includes correct `image_count` and `cover_image` fields.

## Verification

```bash
pytest tests/unit/test_album_service.py -v -k "cover or listing"
# All tests should FAIL (Red)
```
