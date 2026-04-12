# BDD Specifications — Album Feature

## Feature: Album CRUD

### Scenario: Create a manual album

```gherkin
Given the system has no albums
When I create an album with name "Vacation 2025" and type "manual"
Then the album is created with id > 0
And the album type is "manual"
And the album rule_logic is null
And the album image_count is 0
```

### Scenario: Create a smart album with AND logic

```gherkin
Given the system has tags "sunset", "beach", "mountain"
When I create an album with name "Beach Sunsets" and type "smart" and rule_logic "and"
And I set rules: include "sunset", include "beach"
Then the album is created with type "smart" and rule_logic "and"
And the album has 2 rules
```

### Scenario: Create a smart album with OR logic

```gherkin
Given the system has tags "cat", "dog"
When I create an album with name "Pets" and type "smart" and rule_logic "or"
And I set rules: include "cat", include "dog"
Then the album is created with type "smart" and rule_logic "or"
```

### Scenario: Album name must be unique

```gherkin
Given an album named "My Album" exists
When I create an album with name "My Album"
Then the request fails with 409 Conflict
```

### Scenario: Album name must not be empty

```gherkin
When I create an album with name ""
Then the request fails with 422 Validation Error
```

### Scenario: Update album name and description

```gherkin
Given an album named "Old Name" exists
When I update the album name to "New Name" and description to "Updated"
Then the album name is "New Name"
And the album description is "Updated"
And the album updated_at is newer than created_at
```

### Scenario: Delete album does not delete images

```gherkin
Given a manual album "Travel" with 3 images
When I delete the album "Travel"
Then the album no longer exists
And all 3 images still exist in the images table
```

## Feature: Manual Album Image Management

### Scenario: Add images to manual album

```gherkin
Given a manual album "Favorites" exists
And 3 indexed images exist
When I add all 3 images to "Favorites"
Then the album image_count is 3
```

### Scenario: Image can belong to multiple albums

```gherkin
Given manual albums "Album A" and "Album B" exist
And an indexed image with hash "abc123" exists
When I add "abc123" to "Album A"
And I add "abc123" to "Album B"
Then "Album A" contains "abc123"
And "Album B" contains "abc123"
```

### Scenario: Remove image from manual album

```gherkin
Given a manual album "Favorites" with image "abc123"
When I remove "abc123" from "Favorites"
Then the album image_count is 0
And image "abc123" still exists in the images table
```

### Scenario: Cannot add images to smart album

```gherkin
Given a smart album "Auto Pets" exists
When I try to add image "abc123" to "Auto Pets"
Then the request fails with 400 Bad Request
And the error message indicates smart albums do not support manual image management
```

### Scenario: Adding duplicate image is idempotent

```gherkin
Given a manual album "Favorites" with image "abc123"
When I add "abc123" to "Favorites" again
Then no error occurs
And the album image_count is still 1
```

### Scenario: Bulk add images to album

```gherkin
Given a manual album "Batch" exists
And 10 indexed images exist
When I add all 10 images to "Batch" in a single request
Then the album image_count is 10
```

## Feature: Manual Album Pagination

### Scenario: Paginate album images with cursor

```gherkin
Given a manual album "Large" with 25 images
When I request album images with limit 10
Then I receive 10 images and a next_cursor
When I request album images with limit 10 and cursor = next_cursor
Then I receive 10 more images and a next_cursor
When I request album images with the second cursor
Then I receive 5 images and next_cursor is null
```

## Feature: Smart Album Rules

### Scenario: AND logic — all included tags required

```gherkin
Given tags "sunset" and "beach" exist
And image "img1" has tags ["sunset", "beach"]
And image "img2" has tags ["sunset"]
And image "img3" has tags ["beach"]
And a smart album "Beach Sunsets" with rule_logic "and" and rules: include "sunset", include "beach"
When I list images in "Beach Sunsets"
Then only "img1" is returned
```

### Scenario: OR logic — any included tag matches

```gherkin
Given tags "cat" and "dog" exist
And image "img1" has tags ["cat"]
And image "img2" has tags ["dog"]
And image "img3" has tags ["mountain"]
And a smart album "Pets" with rule_logic "or" and rules: include "cat", include "dog"
When I list images in "Pets"
Then "img1" and "img2" are returned
And "img3" is not returned
```

### Scenario: Exclude tag filters out matching images

```gherkin
Given tags "landscape", "urban" exist
And image "img1" has tags ["landscape"]
And image "img2" has tags ["landscape", "urban"]
And a smart album with rule_logic "or", rules: include "landscape", exclude "urban"
When I list images in the album
Then only "img1" is returned
```

### Scenario: AND with exclude — must have all includes, none of excludes

```gherkin
Given tags "food", "dessert", "savory" exist
And image "img1" has tags ["food", "dessert"]
And image "img2" has tags ["food", "savory"]
And image "img3" has tags ["food", "dessert", "savory"]
And a smart album with rule_logic "and", rules: include "food", include "dessert", exclude "savory"
When I list images in the album
Then only "img1" is returned
```

### Scenario: Rule changes are immediately reflected

```gherkin
Given a smart album "Dynamic" with rule_logic "or" and rules: include "sunset"
And image "img1" has tag "sunset"
When I list images in "Dynamic"
Then "img1" is returned
When I add tag "beach" to "img1"
And I update rules to: include "beach" (removing "sunset")
And I list images in "Dynamic"
Then "img1" is still returned (now matches via "beach")
```

### Scenario: Deleting a tag updates smart album results

```gherkin
Given a smart album with rule_logic "and", rules: include tag "sunset" (id=1), include tag "beach" (id=2)
And image "img1" has tags ["sunset", "beach"]
When tag "sunset" is deleted
Then the rule referencing "sunset" is also deleted (CASCADE)
And listing the album now uses only the remaining "beach" rule
And "img1" still matches (has "beach")
```

### Scenario: Smart album with no rules returns no images

```gherkin
Given a smart album "Empty Rules" with no rules defined
When I list images in "Empty Rules"
Then 0 images are returned
```

### Scenario: Cannot remove images from smart album

```gherkin
Given a smart album "Auto" exists
When I try to remove image "abc123" from "Auto"
Then the request fails with 400 Bad Request
```

## Feature: Cover Image

### Scenario: Manual album cover is first image by sort_order

```gherkin
Given a manual album "Travel" with images added in order: "img1", "img2", "img3"
When I list albums
Then "Travel" has cover_image matching "img1"
```

### Scenario: Smart album cover is first image in query result

```gherkin
Given a smart album "Sunsets" matching images "img_a", "img_b" (ordered by canonical_path)
When I list albums
Then "Sunsets" has cover_image matching whichever comes first alphabetically
```

### Scenario: Empty album has null cover

```gherkin
Given a manual album "Empty" with no images
When I list albums
Then "Empty" has cover_image = null
```

## Feature: Smart Album Source Paths

### Scenario: Smart album with source paths only matches images in those paths

```gherkin
Given tags "sunset" exists
And image "img1" at path "/images/photos/2025/sunset.jpg" has tag "sunset"
And image "img2" at path "/images/photos/2024/sunset.jpg" has tag "sunset"
And image "img3" at path "/images/videos/sunset.jpg" has tag "sunset"
And a smart album with rule_logic "or", rules: include "sunset", source_paths: ["photos/2025"]
When I list images in the album
Then only "img1" is returned
```

### Scenario: Smart album with multiple source paths

```gherkin
Given tags "landscape" exists
And image "img1" at path "/images/photos/2025/land.jpg" has tag "landscape"
And image "img2" at path "/images/photos/2024/land.jpg" has tag "landscape"
And image "img3" at path "/images/other/land.jpg" has tag "landscape"
And a smart album with source_paths: ["photos/2025", "photos/2024"]
When I list images in the album
Then "img1" and "img2" are returned
And "img3" is not returned
```

### Scenario: Smart album with no source paths matches all images

```gherkin
Given tags "nature" exists
And images in various paths all have tag "nature"
And a smart album with source_paths: [] (empty)
When I list images in the album
Then all images with tag "nature" are returned regardless of path
```

### Scenario: Set source paths for smart album

```gherkin
Given a smart album "Travel" exists
When I set source paths to ["photos/travel", "photos/vacation"]
Then the album has 2 source paths
And listing images only matches within those paths
```

### Scenario: Cannot set source paths for manual album

```gherkin
Given a manual album "Manual" exists
When I try to set source paths for "Manual"
Then the request fails with 400 Bad Request
```

## Feature: Smart Album Edge Cases

### Scenario: Smart album with no include rules returns no images

```gherkin
Given tags "landscape", "urban" exist
And images with various tags exist
And a smart album with rule_logic "or" and rules: exclude "urban" (no include rules)
When I list images in the album
Then 0 images are returned
```

### Scenario: AND album after all include tags deleted returns no images

```gherkin
Given a smart album with rule_logic "and", rules: include tag "sunset" (id=1)
And image "img1" has tag "sunset"
When tag "sunset" is deleted (CASCADE removes the rule)
Then the album has 0 rules
And listing images in the album returns 0 results
```

### Scenario: set_album_rules with empty list clears all rules

```gherkin
Given a smart album "Dynamic" with 3 rules
When I set rules to an empty list
Then the album has 0 rules
And listing images returns 0 results
```

### Scenario: set_album_rules with duplicate tag_id fails

```gherkin
Given a smart album "Test" exists
And tag "sunset" (id=1) exists
When I set rules with two entries for tag_id=1
Then the request fails with 400 Bad Request
```

## Feature: Smart Album Pagination

### Scenario: Paginate smart album images with cursor

```gherkin
Given tags "nature" exists
And 25 images all have tag "nature"
And a smart album with rule_logic "or" and rules: include "nature"
When I request album images with limit 10
Then I receive 10 images and a next_cursor
When I request album images with limit 10 and cursor = next_cursor
Then I receive 10 more images and a next_cursor
When I request album images with the second cursor
Then I receive 5 images and next_cursor is null
```

## Feature: Error Handling

### Scenario: Get non-existent album returns 404

```gherkin
When I request album with id 9999
Then the response status is 404
```

### Scenario: Add non-existent image to album returns 400

```gherkin
Given a manual album "Test" exists
When I add content_hash "nonexistent_hash" to "Test"
Then no error occurs but 0 images are added (INSERT references images table via FK)
```

### Scenario: Set rule with non-existent tag returns 400

```gherkin
Given a smart album "Test" exists
When I set rules with tag_id 9999
Then the request fails with 400 Bad Request
```

### Scenario: Bulk add exceeding limit returns 422

```gherkin
Given a manual album "Test" exists
When I try to add 501 images to "Test"
Then the request fails with 422 Validation Error
```

## Feature: Album Listing

### Scenario: List albums shows image count and cover

```gherkin
Given a manual album "A" with 5 images
And a smart album "B" matching 3 images
And a manual album "C" with 0 images
When I list all albums
Then I receive 3 albums
And album "A" has image_count 5 and a cover_image
And album "B" has image_count 3 and a cover_image
And album "C" has image_count 0 and cover_image null
```

## Testing Strategy

### Unit Tests

- `tests/unit/test_album_service.py` — AlbumService methods with real SQLite (in-memory)
- `tests/unit/test_album_smart_query.py` — Smart album SQL query logic with various tag combinations

### Integration Tests

- `tests/integration/test_album_api.py` — Full API endpoint testing via TestClient
  - Album CRUD endpoints
  - Manual album image add/remove
  - Smart album rule management
  - Smart album image listing with AND/OR/exclude logic
  - Pagination
  - Error cases (adding to smart album, duplicate names)

### Frontend Tests

- `src/image_vector_search/frontend/src/test/AlbumsPage.test.tsx` — Album listing renders correctly
- `src/image_vector_search/frontend/src/test/AlbumImagesPage.test.tsx` — Album detail page and image grid
