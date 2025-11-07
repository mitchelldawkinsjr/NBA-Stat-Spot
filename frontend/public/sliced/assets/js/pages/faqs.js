/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : faqs init Js File                                      *
*------------------------------------------------------------------------
*/

function accordion(index, defaultOpen = false) {
    return {
        isOpen: defaultOpen,
        handleClick() {
            this.isOpen = !this.isOpen;
        },
        handleToggle() {
            console.log(" function called");

            return this.isOpen ? { maxHeight: this.$refs.tab.scrollHeight + 'px' } : { maxHeight: '0px' };
        },
        handleRotate() {
            return this.isOpen ? 'rotate-180' : '';
        }
    };
}