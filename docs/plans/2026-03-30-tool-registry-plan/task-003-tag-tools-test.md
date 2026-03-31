# Task 003: Tag & Category Tools — Tests

**depends-on**: ["001-registry-core-impl"]
**type**: test
**files**:
- `tests/unit/test_tag_tools.py` (create)

## BDD Scenarios

```gherkin
Scenario: Execute manage_tags with action=create
  Given a ToolContext with a TagService
  And the tool "manage_tags" is registered
  When I call the tool with {"action": "create", "name": "landscape"}
  Then it returns a dict with "tag" containing the created Tag
  And the tag has an id, name "landscape", and created_at timestamp

Scenario: Execute manage_tags with action=list
  Given a ToolContext with a TagService containing tags "landscape", "portrait"
  When I call manage_tags with {"action": "list"}
  Then it returns {"tags": [...]} with 2 tag objects

Scenario: Tool raises ValueError for invalid input
  Given the tool "manage_tags" is registered
  When I call it with {"action": "create"} (missing required "name")
  Then it raises ValueError with a message indicating "name" is required

Scenario: Tool raises ValueError for empty tag name
  Given the tool "manage_tags" is registered
  When I call it with {"action": "create", "name": ""}
  Then it raises ValueError with a message about empty name
```

## Steps

1. Create `tests/unit/test_tag_tools.py` with a `FakeTagService` that supports create_tag, list_tags, rename_tag, delete_tag, and category operations
2. Write tests:
   - `test_manage_tags_create` — call with action="create", name="landscape", assert tag returned
   - `test_manage_tags_list` — pre-populate FakeTagService, call with action="list", assert tags returned
   - `test_manage_tags_rename` — call with action="rename", tag_id, new_name, assert ok
   - `test_manage_tags_delete` — call with action="delete", tag_id, assert ok
   - `test_manage_tags_missing_name` — call with action="create" without name, assert ValueError
   - `test_manage_tags_empty_name` — call with action="create", name="", assert ValueError
   - `test_manage_categories_create` — call with action="create", name, assert category returned
   - `test_manage_categories_list` — assert categories returned
   - `test_tag_images_add` — call tag_images with action="add_tag", content_hash, tag_id
   - `test_tag_images_remove` — call tag_images with action="remove_tag"

## Verification

```bash
pytest tests/unit/test_tag_tools.py -v
```

Expected: Tests fail with ImportError (Red phase).
