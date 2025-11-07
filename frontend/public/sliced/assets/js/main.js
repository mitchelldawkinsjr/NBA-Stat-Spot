/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : Main Js file of the template                           *
*------------------------------------------------------------------------
*/

(function () {
    ("use strict");

    document.addEventListener("alpine:init", () => {
        Alpine.data("collapse", () => ({
            collapse: false,

            collapseSidebar() {
                this.collapse = !this.collapse;
            },
        }));
        Alpine.data("dropdown", (initialOpenState = false) => ({
            open: initialOpenState,

            toggle() {
                this.open = !this.open;
            },
        }));
        Alpine.data("modals", (initialOpenState = false) => ({
            open: initialOpenState,
            toggle() {
                this.open = !this.open;
            },
        }));

        // main - custom functions
        Alpine.data("main", (value) => { });

        Alpine.store("app", {
            // sidebar
            sidebar: false,
            toggleSidebar() {
                this.sidebar = !this.sidebar;
            },
            // Light and dark Mode
            mode: Alpine.$persist('light'),
            sidebarMode: Alpine.$persist('light'),
            layout: Alpine.$persist('vertical'),
            direction: Alpine.$persist('ltr'),
            showSettings: false,
            toggleMode(val) {
                if (!val)
                    val = this.mode || "light"; // light And Dark
                this.mode = val;
            },

            toggleFullScreen() {
                if (document.fullscreenElement) {
                    document.exitFullscreen();
                } else {
                    document.documentElement.requestFullscreen();
                }
            },

            setLayout() {
                // Set the layout based on current settings
                this.layout = this.layout || 'vertical';
                this.mode = this.mode || 'light';
                this.sidebarMode = this.sidebarMode || 'light';
                this.direction = this.direction || 'ltr';
                this.open = false;
            },

            resetLayout() {
                // Reset to default layout settings
                this.layout = 'vertical';
                this.mode = 'light';
                this.sidebarMode = 'light';
                this.direction = 'ltr';
                this.open = false;
            }
        });

        Alpine.store('sidebar', {
            activeMenu: localStorage.getItem('activeMenu') || '',
            activeSubMenu: localStorage.getItem('activeSubMenu') || '',
            isSubmenu: false,
            toggleMenu(menu, isSubmenu) {
                const currentPath = window.location.pathname;
                this.isSubmenu = isSubmenu;
                if (isSubmenu) {
                    if (this.activeMenu && this.activeMenu === this.getParentMenu(currentPath)) {
                        this.activeSubMenu = this.activeSubMenu === menu ? '' : menu;
                        localStorage.setItem('activeSubMenu', this.activeSubMenu);
                        console.log("Submenu toggled:", this.activeSubMenu);
                    }
                } else {
                    localStorage.removeItem('activeSubMenu');
                    const isSameMenu = this.activeMenu === menu;
                    this.activeMenu = isSameMenu ? '' : menu;
                    localStorage.setItem('activeMenu', this.activeMenu);
                    console.log("Main menu toggled:", this.activeMenu);
                }
            },
    
            getParentMenu() {
                return this.activeMenu;
            },
    
            isSubMenuActive(menu) {
                return this.activeSubMenu === menu;
            },
            setActiveClass() {
                let currentPath = window.location.pathname;
            
                if (currentPath === '/') {
                    currentPath = 'index.html'; // Set to index.html for root
                    this.toggleMenu('dashboard');
                } else {
                    currentPath = currentPath.substring(currentPath.lastIndexOf('/') + 1); // Extract the last part of the path
                }
            
                const activeItem = document.querySelector(`.sidebar ul li a[href="${currentPath}"]`);
            
                if (activeItem) {
                    const mainMenuItem = activeItem.closest('li.main-menu');
                    const submenuItem = activeItem.closest('li.subMenu');
                    
                    activeItem.classList.add('active');
                    this.isSubmenu = false;
                    console.log("submenuItem", submenuItem);
                    
                    console.log("mainMenuItem", mainMenuItem);
                    if (!submenuItem) {
                        this.activeSubMenu = '';
                        this.isSubMenuActive(this.activeSubMenu);
                        localStorage.removeItem('activeSubMenu');
                    }

                } else {
                    this.activeMenu = '';
                    this.activeSubMenu = '';
                    localStorage.removeItem('activeMenu');
                }
            }
        });
    
        Alpine.data('sidebarMenu', () => ({
            init() {
                this.$store.sidebar.setActiveClass();
                if (window.location.pathname === '/') {
                    this.$store.sidebar.activeMenu = localStorage.getItem('activeMenu') || 'dashboard';
                }
            },
            isActive(menu) {
                return this.$store.sidebar.activeMenu === menu;
            },
            isSubMenuActive(menu) {
                return this.$store.sidebar.activeSubMenu === menu;
            },
            toggle(menu, isSubmenu) {
                this.$store.sidebar.toggleMenu(menu, isSubmenu);
            }
        }));
    });

    window.Alpine.start();

})();
