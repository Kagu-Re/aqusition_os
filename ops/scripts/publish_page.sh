#!/bin/bash
# Bash script to publish a page step-by-step
# Usage: ./ops/scripts/publish_page.sh p1 acq.db

set -e

PAGE_ID="${1:-p1}"
DB="${2:-acq.db}"

export PYTHONPATH=src

echo "========================================"
echo "  Page Publishing Walkthrough"
echo "========================================"
echo ""

# Step 1: Record events
echo "[1/4] Recording test events..."
for event in call_click quote_submit thank_you_view; do
    echo "  Recording $event..."
    python -m ae.cli record-event \
        --db "$DB" \
        --page-id "$PAGE_ID" \
        --event-name "$event" \
        --params-json '{"test":true}'
done
echo "  ✓ All events recorded"
echo ""

# Step 2: Validate
echo "[2/4] Validating page..."
python -m ae.cli validate-page --db "$DB" --page-id "$PAGE_ID"
echo "  ✓ Validation passed"
echo ""

# Step 3: Publish
echo "[3/4] Publishing page..."
python -m ae.cli publish-page --db "$DB" --page-id "$PAGE_ID"
echo "  ✓ Page published successfully"
echo ""

# Step 4: Verify output
echo "[4/4] Verifying published file..."
OUTPUT_PATH="exports/static_site/$PAGE_ID/index.html"
if [ -f "$OUTPUT_PATH" ]; then
    echo "  ✓ Published file found"
    echo "  Location: $(realpath "$OUTPUT_PATH")"
    echo "  Size: $(stat -f%z "$OUTPUT_PATH" 2>/dev/null || stat -c%s "$OUTPUT_PATH" 2>/dev/null || echo "unknown") bytes"
else
    echo "  ⚠ Published file not found at: $OUTPUT_PATH"
    echo "  Check if publish succeeded"
fi

echo ""
echo "========================================"
echo "  Publishing Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Open: $OUTPUT_PATH"
echo "  2. Or serve with: cd exports/static_site/$PAGE_ID && python -m http.server 8080"
echo "  3. Then visit: http://localhost:8080/index.html"
