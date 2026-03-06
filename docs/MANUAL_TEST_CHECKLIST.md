# Manual Testing Checklist for UX/UI Improvements

## Prerequisites

1. **Start the Console Server**:
   ```powershell
   $env:PYTHONPATH="src"
   $env:AE_DB_PATH="acq.db"
   python -m ae.console_app
   ```

2. **Open Browser**: Navigate to `http://localhost:8000/console`

3. **Open Developer Tools**: Press `F12` to open browser DevTools

## Test Checklist

### ✅ Test 1: Skip Link (Accessibility)

**Steps:**
1. Load the console page
2. Press `Tab` key once
3. Look for "Skip to main content" link at the top

**Expected:**
- ✅ Skip link appears and is visible
- ✅ Has cyan focus outline
- ✅ Pressing `Enter` jumps to main content

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 2: Keyboard Navigation & Focus Indicators

**Steps:**
1. Press `Tab` repeatedly to navigate through page
2. Observe focus indicators on each element

**Expected:**
- ✅ All interactive elements show cyan outline when focused
- ✅ Focus outline is 2px solid with glow effect
- ✅ Tab order is logical (top to bottom, left to right)
- ✅ Can activate buttons with `Enter` or `Space`

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 3: Mobile Menu Toggle

**Steps:**
1. Resize browser window to < 1024px width (or use mobile device)
2. Look for hamburger menu button in top-left corner
3. Click hamburger button
4. Click outside sidebar
5. Resize back to desktop size

**Expected:**
- ✅ Hamburger button appears on mobile
- ✅ Sidebar slides in from left when clicked
- ✅ Sidebar closes when clicking outside
- ✅ Hamburger button hidden on desktop (>1024px)
- ✅ Sidebar always visible on desktop

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 4: Form Validation (Landing Pages)

**Steps:**
1. Navigate to `/landing-pages` route (click sidebar link or go to `#/landing-pages`)
2. Leave Page ID field empty
3. Click "Create Landing Page" button
4. Observe error message
5. Enter invalid URL (e.g., "not-a-url") in Page URL field
6. Tab away from field (blur event)
7. Fill all required fields correctly
8. Click "Create Landing Page"

**Expected:**
- ✅ Empty required field shows red border
- ✅ Error message appears below field: "This field is required"
- ✅ Invalid URL shows error: "Please enter a valid URL"
- ✅ Error messages clear when field becomes valid
- ✅ Button shows spinner and "Creating..." text during submission
- ✅ Button is disabled during submission
- ✅ Form resets after successful submission

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 5: ARIA Attributes

**Steps:**
1. Open browser DevTools (F12)
2. Go to Elements/Inspector tab
3. Check form elements for ARIA attributes
4. Check buttons for aria-label
5. Check status elements for aria-live

**Expected:**
- ✅ Form inputs have `aria-required="true"` on required fields
- ✅ Form inputs have `aria-invalid` attribute
- ✅ Form inputs have `aria-describedby` pointing to error messages
- ✅ Buttons have `aria-label` or visible text
- ✅ Status elements have `aria-live="polite"`
- ✅ Navigation has `role="navigation"`
- ✅ Main content has `role="main"`

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 6: Button Loading States

**Steps:**
1. Go to Landing Pages form
2. Fill form with valid data
3. Click "Create Landing Page"
4. Observe button during submission

**Expected:**
- ✅ Button shows spinner icon
- ✅ Button text changes to "Creating..."
- ✅ Button has `aria-busy="true"` attribute
- ✅ Button is disabled (can't click again)
- ✅ Button returns to normal after completion

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 7: Status Indicators

**Steps:**
1. Look at Status card in dashboard
2. Check health status display

**Expected:**
- ✅ Health status shows "OK" or "ERR"
- ✅ Status dot is visible (green/yellow/red)
- ✅ Status has `aria-live` attribute for screen readers
- ✅ Version badge displays correctly

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 8: Form Field Labels & Help Text

**Steps:**
1. Go to Landing Pages form
2. Check each form field

**Expected:**
- ✅ All fields have visible labels
- ✅ Required fields marked with red asterisk (*)
- ✅ Labels properly associated with inputs (`for` attribute)
- ✅ Help text appears below some fields (e.g., Status, Locale)
- ✅ Help text has `aria-describedby` connection

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 9: Error Handling

**Steps:**
1. Try to submit form with invalid data
2. Disconnect network and try to submit
3. Check error messages

**Expected:**
- ✅ Inline validation errors appear immediately
- ✅ Network errors show toast notification
- ✅ Error messages are user-friendly (not technical)
- ✅ Errors don't break the UI
- ✅ Can recover from errors (form still usable)

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 10: Responsive Design

**Steps:**
1. Test on desktop (1920x1080)
2. Test on tablet (768x1024)
3. Test on mobile (375x667)
4. Check all breakpoints

**Expected:**
- ✅ Desktop: Sidebar visible, forms in 2 columns
- ✅ Tablet: Hamburger menu, forms stack to 1 column
- ✅ Mobile: All content accessible, buttons large enough
- ✅ Text readable at all sizes
- ✅ No horizontal scrolling

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 11: Browser Console Check

**Steps:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Check for errors
4. Navigate through pages
5. Submit forms

**Expected:**
- ✅ No JavaScript errors on page load
- ✅ No errors when navigating
- ✅ No errors when submitting forms
- ✅ Router logs show successful page loads
- ✅ No CSS loading errors

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

### ✅ Test 12: Visual Design Consistency

**Steps:**
1. Navigate through different pages
2. Check button styles
3. Check card styles
4. Check color scheme

**Expected:**
- ✅ All buttons use consistent styles
- ✅ Cards have hover effects
- ✅ Color scheme is consistent (Akira theme)
- ✅ Focus indicators match design system
- ✅ Loading spinners are consistent

**Status:** [ ] Pass [ ] Fail
**Notes:** _________________________________

---

## Quick Test Script (Browser Console)

Open browser console (F12) and run:

```javascript
// Test 1: Check for skip link
console.log('Skip link:', document.querySelector('.skip-link') ? '✅ Found' : '❌ Missing');

// Test 2: Check for mobile menu
console.log('Mobile menu:', document.getElementById('mobile-menu-toggle') ? '✅ Found' : '❌ Missing');

// Test 3: Check ARIA attributes
const ariaCount = document.querySelectorAll('[aria-label], [aria-required], [aria-live]').length;
console.log('ARIA attributes:', ariaCount > 0 ? `✅ Found ${ariaCount}` : '❌ Missing');

// Test 4: Check form validation
const form = document.getElementById('create-page-form');
if (form) {
  const fields = form.querySelectorAll('[aria-required="true"]');
  console.log('Required fields:', fields.length > 0 ? `✅ Found ${fields.length}` : '❌ Missing');
}

// Test 5: Check focus styles
const testEl = document.querySelector('input');
if (testEl) {
  testEl.focus();
  const style = window.getComputedStyle(testEl);
  console.log('Focus outline:', style.outline !== 'none' ? '✅ Visible' : '❌ Missing');
  testEl.blur();
}

// Test 6: Check page container
console.log('Page container:', document.getElementById('page-container') ? '✅ Found' : '❌ Missing');
```

## Test Results Summary

**Total Tests:** 12
**Passed:** _____
**Failed:** _____
**Notes:** _________________________________

## Issues Found

1. _________________________________
2. _________________________________
3. _________________________________

## Browser & Environment

- **Browser:** ________________
- **Version:** ________________
- **OS:** ________________
- **Screen Size:** ________________
