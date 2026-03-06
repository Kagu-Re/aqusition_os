# UX/UI Testing Guide

## Quick Start

### 1. Start the Console Server

```powershell
# Set environment variables
$env:PYTHONPATH="src"
$env:AE_DB_PATH="acq.db"

# Start console server
python -m ae.console_app
# Or with uvicorn:
# uvicorn ae.console_app:app --host 127.0.0.1 --port 8000
```

### 2. Access the Console

Open your browser and navigate to:
```
http://localhost:8000/console
```

## Testing Checklist

### ✅ Accessibility Testing

#### Keyboard Navigation
- [ ] **Tab Navigation**: Press `Tab` to navigate through all interactive elements
  - Should see visible cyan outline on focused elements
  - Tab order should be logical (top to bottom, left to right)
  
- [ ] **Skip Link**: Press `Tab` when page loads
  - Should see "Skip to main content" link at top
  - Press `Enter` to skip to main content
  - Should jump past sidebar navigation

- [ ] **Form Navigation**: Navigate to Landing Pages form
  - Tab through all form fields
  - Each field should show focus indicator
  - Required fields should be clearly marked

- [ ] **Button Focus**: Tab to buttons
  - All buttons should show focus outline
  - Can activate buttons with `Enter` or `Space`

#### Screen Reader Testing (Optional)
- [ ] Use NVDA/JAWS or browser screen reader
- [ ] Navigate through forms - labels should be announced
- [ ] Error messages should be announced when validation fails
- [ ] Status updates should be announced

#### Mobile Menu
- [ ] **Desktop (>1024px)**: Sidebar should be visible
- [ ] **Mobile (<1024px)**: 
  - Sidebar should be hidden by default
  - Hamburger menu button should appear in top-left
  - Click hamburger to open sidebar
  - Click outside sidebar to close
  - Menu button should show `aria-expanded` state

### ✅ Form Validation Testing

#### Landing Pages Form
1. Navigate to `/landing-pages` route
2. **Test Required Fields**:
   - [ ] Leave Page ID empty, click "Create Landing Page"
   - Should see red border on Page ID field
   - Should see error message "This field is required"
   - Error should be announced to screen readers

3. **Test URL Validation**:
   - [ ] Enter invalid URL (e.g., "not-a-url") in Page URL field
   - [ ] Tab away from field (blur event)
   - Should see error "Please enter a valid URL"
   - Should see red border

4. **Test Real-time Validation**:
   - [ ] Fill in Page ID field
   - [ ] Tab away (blur)
   - If invalid, should show error immediately
   - If valid, error should clear

5. **Test Form Submission**:
   - [ ] Fill all required fields correctly
   - [ ] Click "Create Landing Page"
   - [ ] Button should show spinner and "Creating..." text
   - [ ] Button should be disabled during submission
   - [ ] After success, form should reset
   - [ ] After error, button should return to normal state

### ✅ Button Loading States

#### Test Async Operations
1. **Create Landing Page**:
   - [ ] Click "Create Landing Page" button
   - [ ] Button should show spinner
   - [ ] Button text should change to "Creating..."
   - [ ] Button should be disabled
   - [ ] `aria-busy="true"` should be set

2. **Load Pages**:
   - [ ] Click "Load Pages" button
   - [ ] Should see loading spinner in list area
   - [ ] After load, spinner should disappear

3. **Other Actions**:
   - [ ] Test "Validate" button on existing pages
   - [ ] Test "Publish" button
   - [ ] All should show appropriate loading feedback

### ✅ Visual Design Testing

#### Focus Indicators
- [ ] **Keyboard Focus**: Tab through page
  - All focused elements should show cyan outline
  - Outline should be 2px solid
  - Should have glow effect

- [ ] **Mouse Focus**: Click on inputs
  - Should show cyan border and glow
  - Should NOT show outline (only keyboard shows outline)

#### Color Contrast
- [ ] **Text Readability**:
  - Primary text (#e0e0e8) should be readable on dark background
  - Muted text (#8888a0) should be readable
  - Status colors should be clearly visible

- [ ] **Status Indicators**:
  - Health status dot should be visible
  - Status colors (green/yellow/red) should be clear

#### Responsive Design
- [ ] **Desktop (1920x1080)**:
  - Sidebar visible
  - Content properly spaced
  - Forms in 2-column layout

- [ ] **Tablet (768x1024)**:
  - Sidebar should hide
  - Hamburger menu should appear
  - Forms should stack to 1 column

- [ ] **Mobile (375x667)**:
  - All content should be accessible
  - Buttons should be large enough to tap
  - Forms should be single column
  - Text should be readable

### ✅ Error Handling Testing

#### Form Errors
- [ ] **Required Field Errors**:
  - Submit form with empty required fields
  - Should see inline error messages
  - Should see red borders
  - Should focus first invalid field

- [ ] **URL Validation Errors**:
  - Enter invalid URL format
  - Should see specific error message
  - Should prevent form submission

#### API Errors
- [ ] **Network Errors**:
  - Disconnect network
  - Try to create landing page
  - Should see toast error message
  - Button should return to normal state

- [ ] **Server Errors**:
  - Use invalid data that causes server error
  - Should see user-friendly error message
  - Should not break UI

### ✅ Navigation Testing

#### Router Navigation
- [ ] **Hash Routing**:
  - Navigate to `/landing-pages`
  - URL should show `#/landing-pages`
  - Page should load correctly
  - Embedded sections should be hidden

- [ ] **Default View**:
  - Navigate to `/` or no hash
  - Should show embedded sections
  - Page container should be hidden

- [ ] **Navigation Links**:
  - Click sidebar links
  - Should navigate correctly
  - Active state should update
  - Page should load without refresh

#### Mobile Navigation
- [ ] **Hamburger Menu**:
  - On mobile, click hamburger
  - Sidebar should slide in from left
  - Click outside to close
  - Click hamburger again to toggle

### ✅ Status Updates Testing

#### Health Status
- [ ] **Status Display**:
  - Should show health status
  - Should update automatically
  - Should be announced to screen readers (`aria-live`)

- [ ] **Status Colors**:
  - OK status should be green
  - Error status should be red
  - Warning status should be yellow

## Common Issues to Check

### Potential Problems

1. **JavaScript Errors**:
   - Open browser console (F12)
   - Check for any errors
   - Form validation should not throw errors

2. **CSS Issues**:
   - Check if styles load correctly
   - Focus indicators should be visible
   - Mobile menu should work smoothly

3. **ARIA Issues**:
   - Use browser DevTools accessibility inspector
   - Check for missing ARIA labels
   - Verify ARIA attributes are set correctly

4. **Form Issues**:
   - Test with empty form
   - Test with invalid data
   - Test with valid data
   - All should work correctly

## Browser Compatibility

Test in:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if on Mac)
- [ ] Mobile browsers (iOS Safari, Chrome Mobile)

## Performance Testing

- [ ] **Page Load**: Should load quickly
- [ ] **Form Submission**: Should respond within 2 seconds
- [ ] **Navigation**: Should be instant (no page reload)
- [ ] **Animations**: Should be smooth (60fps)

## Reporting Issues

If you find issues, note:
1. **Browser and Version**: e.g., Chrome 120
2. **Screen Size**: e.g., 1920x1080 or mobile
3. **Steps to Reproduce**: Detailed steps
4. **Expected Behavior**: What should happen
5. **Actual Behavior**: What actually happens
6. **Console Errors**: Any JavaScript errors
7. **Screenshots**: If visual issues

## Quick Test Script

Run through this quick test:

```javascript
// Open browser console and run:

// 1. Test skip link
document.querySelector('.skip-link').focus();

// 2. Test form validation
const form = document.getElementById('create-page-form');
const pageId = document.getElementById('page_id');
pageId.value = '';
pageId.dispatchEvent(new Event('blur'));

// 3. Test mobile menu toggle
const menuToggle = document.getElementById('mobile-menu-toggle');
menuToggle.click();

// 4. Test focus indicators
document.querySelectorAll('input, button, a').forEach(el => {
  el.focus();
  console.log('Focused:', el.id || el.textContent);
  el.blur();
});
```

## Success Criteria

All tests should pass:
- ✅ Keyboard navigation works smoothly
- ✅ Focus indicators are visible
- ✅ Form validation works correctly
- ✅ Button loading states work
- ✅ Mobile menu functions properly
- ✅ No console errors
- ✅ All ARIA attributes present
- ✅ Responsive design works
- ✅ Error messages are clear
- ✅ Status updates are announced
