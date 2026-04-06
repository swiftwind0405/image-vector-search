# Task 010: Frontend Routing and Navigation — Implementation

**type:** impl  
**depends-on:** ["009"]

## Goal

Wire `SettingsPage` into the React app router and add a "Settings" navigation item to the sidebar.

## BDD Scenario

```gherkin
Scenario: Admin navigates to Settings page
  Given the admin is authenticated
  When the admin clicks "Settings" in the sidebar
  Then the URL changes to /settings
  And the SettingsPage renders
```

## Files to Modify

- `src/image_search_mcp/web/src/App.tsx`
- `src/image_search_mcp/web/src/components/Layout.tsx`

## What to Implement

### `App.tsx`

Add a new `<Route>` inside the `AuthGuard` block:
```
path="settings" element={<SettingsPage />}
```

Import `SettingsPage` from `"./pages/SettingsPage"`.

### `Layout.tsx`

Add a Settings nav item to `navItems` array:
```typescript
{ to: "/settings", icon: Settings, label: "Settings" }
```

Import `Settings` icon from `lucide-react`.

Place it at the bottom of the navigation items list (above the sign-out button), or after "Images".

## Verification

```bash
cd src/image_search_mcp/web && npm test -- admin-navigation
npx tsc --noEmit
```

Existing `admin-navigation.test.tsx` tests should continue passing. TypeScript must compile without errors.
