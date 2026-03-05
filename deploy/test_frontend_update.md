# Frontend Update Test

## What to Check

### 1. Hard Refresh the Page
- Press Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Or clear browser cache for politiquera.com

### 2. Open Data Options Panel
- Click the "Data Options" button in the top right
- Look at the Election dropdown

### 3. Check for Year Separators
You should see year separators (dashed lines) between different years in the dropdown:
```
2026 Primary - Complete Election
2026 Primary - Early Voting
2026 Primary - Mail-In
─────────────────────────────
2024 Primary - Complete Election
2024 Primary - Early Voting
...
```

### 4. Select Combined Dataset
- Select "2026 Primary - Complete Election" from the dropdown
- Look below the dataset info badges

### 5. Check for Method Breakdown
You should see blue badges showing the breakdown:
```
[Hidalgo] [2026] [Primary - Complete Election]

[Early: 61,527] [Mail-In: 1,341]
```

The method breakdown badges should be:
- Blue background (#e8f4f8)
- Blue text (#0066cc)
- Separated by small gaps
- Only visible when combined dataset is selected

### 6. Select Individual Dataset
- Select "2026 Primary - Early Voting" from the dropdown
- The method breakdown should disappear (only show for combined datasets)

## Expected Behavior

### Combined Dataset Selected
```
County: Hidalgo
Year: 2026
Type: Primary - Complete Election

Method Breakdown:
Early: 61,527 | Mail-In: 1,341
```

### Individual Dataset Selected
```
County: Hidalgo
Year: 2026
Type: Primary - Early Voting

(No method breakdown shown)
```

## After Uploading Election Day Data

Once you upload the election day data, the combined dataset should show:
```
Early: 61,527 | Mail-In: 1,341 | Election Day: 23,029
```

## Troubleshooting

### If you don't see the updates:
1. Check browser console (F12) for JavaScript errors
2. Verify the version in the URL: `ui.js?v=20260305c`
3. Try incognito/private browsing mode
4. Clear all browser cache and cookies for politiquera.com

### If method breakdown doesn't appear:
1. Check browser console for errors
2. Verify the API response includes `methodBreakdown`
3. Make sure you selected a combined dataset (not individual)

## API Test
You can test the API directly:
```bash
curl 'https://politiquera.com/api/elections?county=Hidalgo' | python3 -m json.tool
```

Look for:
- `"votingMethod": "combined"`
- `"methodBreakdown": { ... }`
