/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : crousel init Js File                                   *
*------------------------------------------------------------------------
*/

var swiper = new Swiper(".SwiperDefault", {});
var swiper = new Swiper(".SwiperwithArrows", {
    loop: true,
    navigation: {
        nextEl: ".swiper-button-next",
        prevEl: ".swiper-button-prev",
    },
});
var swiper = new Swiper(".SwiperwithPagination", {
    pagination: {
        el: ".swiper-pagination",
    },
});
var swiper = new Swiper(".SwiperwithProgress", {
    pagination: {
        el: ".swiper-pagination",
        type: "progressbar",
    },
    navigation: {
        nextEl: ".swiper-button-next",
        prevEl: ".swiper-button-prev",
    },
});
var swiper = new Swiper(".SwiperMultiple", {
    slidesPerView: 1,
    spaceBetween: 30,
    pagination: {
        el: ".swiper-pagination",
        clickable: true,
    },

    breakpoints: {
        768: {
            slidesPerView: 2,
            spaceBetween: 30
        }
    }
});