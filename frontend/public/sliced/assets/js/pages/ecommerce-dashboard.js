/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : ecommerce dashboard init Js File                       *
*------------------------------------------------------------------------
*/

//Product Views
var options = {
    series: [{
        name: 'Views',
        data: [44, 55, 57, 56, 61, 58, 63, 72, 54, 49, 57]
    }],
    chart: {
        type: 'bar',
        height: 235,
        sparkline: { enabled: !0 },
    },
    plotOptions: {
        bar: {
            horizontal: false,
            columnWidth: '55%',
            endingShape: 'rounded'
        },
    },
    dataLabels: {
        enabled: false
    },
    stroke: {
        show: true,
        width: 2,
        colors: ['transparent']
    },
    xaxis: {
        categories: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    }
};

var chart = new ApexCharts(document.querySelector("#productViewsCharts"), options);
chart.render();

//Users by Device
var options = {
    series: [44, 55, 67, 32],
    chart: {
        height: 270,
        type: "donut",
    },
    colors: ["#0ea5e9", "#50cd89", "#ef4444", "#eab308"],
    legend: {
        position: 'bottom'
    },
    fill: {
        type: 'gradient',
    },
    labels: ["Laptop", "Mobile", "Desktop", "Others"],
};

var chart = new ApexCharts(document.querySelector("#chart6"), options);
chart.render();

//incomeExpenseChart
var options = {
    series: [{
        name: 'Income',
        data: [31, 40, 28, 51, 42, 109, 100]
    }, {
        name: 'Expense',
        data: [11, 32, 45, 32, 34, 52, 41]
    }],
    chart: {
        height: 240,
        type: 'area',
        sparkline: { enabled: !0 },
    },
    dataLabels: {
        enabled: false
    },
    stroke: {
        curve: 'smooth',
        width: 2,
    },
    fill: {
        gradient: {
            enabled: true,
            opacityFrom: 0.55,
            opacityTo: 0
        }
    },
    xaxis: {
        categories: ['Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
    },
    colors: ["#0ea5e9", "#ef4444"],
    tooltip: {
        y: {
            formatter: function (val) {
                return "$" + val + "k"
            }
        }
    }
};

var chart = new ApexCharts(document.querySelector("#incomeExpenseChart"), options);
chart.render();