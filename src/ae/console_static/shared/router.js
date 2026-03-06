// Client-side router for multi-page console UI
// Uses hash-based routing (#/dashboard, #/leads, etc.)

class Router {
  constructor() {
    this.routes = new Map();
    this.currentRoute = null;
    this.pageContainer = null;
    this.hashChangeListenerAdded = false;
    this._handlingRoute = null;
    this.init();
  }

  init() {
    // Wait for DOM to be ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', () => this._initRouter());
    } else {
      this._initRouter();
    }
  }

  _initRouter() {
    // Get page container
    this.pageContainer = document.getElementById('page-container');
    if (!this.pageContainer) {
      console.warn('[Router] Page container not found - retrying in 100ms');
      setTimeout(() => this._initRouter(), 100);
      return;
    }

    console.log('[Router] Initialized successfully');
    console.log('[Router] Current hash:', window.location.hash);
    
    // Listen for hash changes (only add listener once)
    if (!this.hashChangeListenerAdded) {
      window.addEventListener('hashchange', () => {
        console.log('[Router] Hash changed to:', window.location.hash);
        this.handleRoute();
      });
      this.hashChangeListenerAdded = true;
    }
    
    // Don't handle initial route here - wait for routes to be registered
    // The initRouter() function will call handleRoute() after registering routes
  }

  register(path, pageLoader) {
    this.routes.set(path, pageLoader);
  }

  navigate(path) {
    // Ensure path starts with /
    const normalizedPath = path.startsWith('/') ? path : '/' + path;
    console.log('[Router] Navigating to:', normalizedPath);
    window.location.hash = normalizedPath;
    // Also trigger handleRoute immediately in case hashchange doesn't fire
    setTimeout(() => {
      if (this.getCurrentPath() === normalizedPath) {
        this.handleRoute();
      }
    }, 50);
  }

  getCurrentPath() {
    const hash = window.location.hash.slice(1) || '/dashboard';
    return hash.startsWith('/') ? hash : '/' + hash;
  }

  async handleRoute() {
    const path = this.getCurrentPath();
    
    // Prevent duplicate handling of the same route
    if (this._handlingRoute === path) {
      console.log(`[Router] Route ${path} already being handled, skipping duplicate`);
      return;
    }
    
    // Mark as handling
    this._handlingRoute = path;
    
    console.log('[Router] Handling route:', path);
    
    // Update active nav item
    this.updateActiveNav(path);

    // Show/hide embedded sections based on route
    this.toggleEmbeddedSections(path);

    // Find route handler
    const handler = this.routes.get(path);
    
    if (!handler) {
      console.warn(`[Router] Route not found: ${path}, available routes:`, Array.from(this.routes.keys()));
      // Try default route
      const defaultHandler = this.routes.get('/dashboard');
      if (defaultHandler) {
        console.log('[Router] Falling back to dashboard');
        await defaultHandler();
        this.currentRoute = '/dashboard';
        this.navigate('/dashboard');
        return;
      }
      console.error(`[Router] No default route available`);
      this.showError(`Page not found: ${path}`);
      return;
    }

    // Show loading state only if page container is empty or doesn't have rendered content
    if (!this.pageContainer || this.pageContainer.innerHTML.trim().length < 100) {
      this.showLoading();
    }

    try {
      console.log(`[Router] Loading page for route: ${path}`);
      // Load page
      await handler();
      this.currentRoute = path;
      // Mark as rendered after a short delay to allow scripts to execute
      setTimeout(() => {
        if (this.pageContainer) {
          this.pageContainer.setAttribute('data-rendered', 'true');
        }
      }, 500);
      console.log(`[Router] Successfully loaded: ${path}`);
    } catch (error) {
      console.error('[Router] Error loading page:', error);
      this.showError(`Error loading page: ${error.message}`);
    } finally {
      // Clear handling flag
      this._handlingRoute = null;
    }
  }

  toggleEmbeddedSections(path) {
    // Get all embedded sections
    const embeddedSections = document.querySelectorAll('.collapsible-section');
    const pageContainer = this.pageContainer;
    
    // Only show embedded sections when there's no route (default view)
    // All router routes should hide embedded sections and show page container
    const isDefaultView = !path || path === '/' || path === '/dashboard' || (!window.location.hash || window.location.hash === '#' || window.location.hash === '#/');
    
    if (isDefaultView) {
      // Default view: show embedded sections, hide page container
      console.log('[Router] Showing embedded sections (default view)');
      embeddedSections.forEach(section => {
        section.style.display = '';
      });
      if (pageContainer) {
        pageContainer.style.display = 'none';
      }
    } else {
      // Router route: hide embedded sections, show page container
      console.log('[Router] Showing page container for route:', path);
      embeddedSections.forEach(section => {
        section.style.display = 'none';
      });
      if (pageContainer) {
        pageContainer.style.display = '';
        // Ensure it's visible
        pageContainer.style.visibility = 'visible';
        pageContainer.style.opacity = '1';
      }
    }
  }

  updateActiveNav(path) {
    // Remove active class from all nav items
    document.querySelectorAll('.nav-item').forEach(item => {
      item.classList.remove('active');
    });

    // Add active class to current route
    // Try exact match first
    let navItem = document.querySelector(`a[href="#${path}"]`);
    // If not found, try finding by onclick handler
    if (!navItem) {
      document.querySelectorAll('.nav-item').forEach(item => {
        const onclick = item.getAttribute('onclick');
        if (onclick && onclick.includes(`'${path}'`)) {
          navItem = item;
        }
      });
    }
    if (navItem) {
      navItem.classList.add('active');
    }
  }

  showLoading() {
    if (this.pageContainer) {
      this.pageContainer.innerHTML = `
        <div class="empty-state">
          <div class="spinner" style="margin: 0 auto;"></div>
          <div class="empty-state-title mt-4">Loading...</div>
        </div>
      `;
    }
  }

  showError(message) {
    if (this.pageContainer) {
      this.pageContainer.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" style="color: #ff0040;">⚠️</div>
          <div class="empty-state-title" style="color: #ff0040;">Error</div>
          <div class="empty-state-description">${message}</div>
        </div>
      `;
    }
  }

  async loadPage(pagePath) {
    try {
      const url = `/console_static/pages/${pagePath}`;
      console.log(`[Router] Fetching page from: ${url}`);
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error(`Failed to load page: ${response.status} ${response.statusText}`);
      }
      const html = await response.text();
      console.log(`[Router] Page loaded, HTML length: ${html.length}`);
      
      if (this.pageContainer) {
        // Store a flag to prevent overwriting if content is already rendered
        const wasRendered = this.pageContainer.getAttribute('data-rendered') === 'true';
        const hasContent = this.pageContainer.innerHTML.trim().length > 1000; // Has substantial content
        
        // Only clear and reload if this is a fresh load or navigation
        if (!wasRendered || !hasContent) {
          this.pageContainer.innerHTML = html;
          this.pageContainer.setAttribute('data-rendered', 'false');
        } else {
          console.log('[Router] Page already has rendered content, skipping HTML replacement');
        }
        
        // Execute any scripts in the loaded page
        const scripts = this.pageContainer.querySelectorAll('script');
        console.log(`[Router] Found ${scripts.length} script(s) in page`);
        
        // Track executed scripts to prevent duplicates
        const executedScripts = new Set();
        
        scripts.forEach((oldScript, idx) => {
          const scriptContent = oldScript.innerHTML.trim();
          if (!scriptContent) {
            oldScript.remove();
            return;
          }
          
          // Create a hash of the script content to detect duplicates
          const scriptHash = scriptContent.substring(0, 100); // Use first 100 chars as hash
          if (executedScripts.has(scriptHash)) {
            console.log(`[Router] Skipping duplicate script ${idx + 1}`);
            oldScript.remove();
            return;
          }
          executedScripts.add(scriptHash);
          
          try {
            // Create a script element and append to body to ensure global scope
            const newScript = document.createElement('script');
            // Copy all attributes
            Array.from(oldScript.attributes).forEach(attr => {
              newScript.setAttribute(attr.name, attr.value);
            });
            // Set content
            newScript.textContent = scriptContent;
            // Append to body (ensures global scope execution)
            document.body.appendChild(newScript);
            console.log(`[Router] Executed script ${idx + 1} (appended to body)`);
            // Remove the original script from page container
            oldScript.remove();
            // Don't remove scripts from body - they may contain functions that need to persist
            // Scripts will be cleaned up when navigating away or page reloads
          } catch (error) {
            console.error(`[Router] Error executing script ${idx + 1}:`, error);
            oldScript.remove();
          }
        });
      } else {
        throw new Error('Page container not found');
      }
    } catch (error) {
      console.error('[Router] Error loading page:', error);
      throw error;
    }
  }
}

// Global router instance - initialize after DOM is ready
let routerInitialized = false;

function initRouter() {
  if (routerInitialized) return;
  
  // Wait for router class to be available
  if (typeof Router === 'undefined') {
    console.warn('Router class not found, retrying...');
    setTimeout(initRouter, 50);
    return;
  }
  
  routerInitialized = true;
  window.router = new Router();
  
  // Register all page routes BEFORE handling initial route
  window.router.register('/dashboard', () => window.router.loadPage('dashboard.html'));
  window.router.register('/leads', () => window.router.loadPage('leads.html'));
  window.router.register('/events', () => window.router.loadPage('events.html'));
  window.router.register('/revenue', () => window.router.loadPage('revenue.html'));
  window.router.register('/campaigns', () => window.router.loadPage('campaigns.html'));
  window.router.register('/pages', () => window.router.loadPage('pages.html'));
  window.router.register('/landing-pages', () => window.router.loadPage('landing-pages.html'));
  window.router.register('/service-packages', () => window.router.loadPage('service-packages.html'));
  window.router.register('/bot-setup', () => window.router.loadPage('bot-setup.html'));
  window.router.register('/reporting', () => window.router.loadPage('reporting.html'));
  window.router.register('/activity', () => window.router.loadPage('activity.html'));
  window.router.register('/spend', () => window.router.loadPage('spend.html'));
  window.router.register('/alerts', () => window.router.loadPage('alerts.html'));
  window.router.register('/settings', () => window.router.loadPage('settings.html'));
  
  console.log('[Router] Registered routes:', Array.from(window.router.routes.keys()));
  
  // Handle initial route AFTER routes are registered
  // Use requestAnimationFrame to ensure DOM is ready
  requestAnimationFrame(() => {
    if (!window.location.hash || window.location.hash === '#') {
      // Default view: show embedded sections, don't load dashboard.html
      window.router.toggleEmbeddedSections('/');
    } else {
      // Only handle if not already handling
      if (!window.router._handlingRoute) {
        window.router.handleRoute();
      }
    }
  });
}

// Initialize router when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initRouter);
} else {
  // Small delay to ensure all scripts are loaded
  setTimeout(initRouter, 50);
}

// Fallback: if router doesn't initialize after 2 seconds, show error
setTimeout(() => {
  if (!routerInitialized && !window.router) {
    console.error('[Router] Failed to initialize after 2 seconds');
    const container = document.getElementById('page-container');
    if (container) {
      container.innerHTML = `
        <div class="empty-state">
          <div class="empty-state-icon" style="color: #ff0040;">⚠️</div>
          <div class="empty-state-title" style="color: #ff0040;">Router Failed to Load</div>
          <div class="empty-state-description">
            <p>The router script failed to load. Please:</p>
            <ol style="text-align: left; margin-top: 1rem;">
              <li>Hard refresh the page (Ctrl+Shift+R or Cmd+Shift+R)</li>
              <li>Check browser console for errors</li>
              <li>Verify router.js is accessible at /console_static/shared/router.js</li>
            </ol>
          </div>
        </div>
      `;
    }
  }
}, 2000);

// Helper function for navigation
function navigateTo(path) {
  if (window.router) {
    window.router.navigate(path);
  } else {
    window.location.hash = path;
    // Retry after router initializes
    setTimeout(() => {
      if (window.router) {
        window.router.handleRoute();
      }
    }, 100);
  }
}
