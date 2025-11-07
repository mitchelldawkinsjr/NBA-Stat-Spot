/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : real estate init Js File                               *
*------------------------------------------------------------------------
*/

// Chart Widget 1
var options = {
    series: [
        {
            data: [10, 82, 40, 65, 20, 89, 40, 20, 70, 98],
        },
    ],
    chart: {
        height: 60,
        type: "line",
        fontFamily: "Nunito, sans-serif",
        sparkline: {
            enabled: true,
        },
        dropShadow: {
            enabled: false,
        },
    },
    stroke: {
        curve: "smooth",
        width: 2,
    },
    colors: ["#50cd89"],
    grid: {
        padding: {
            top: 5,
            bottom: 5,
            left: 5,
            right: 5,
        },
    },
    tooltip: {
        x: {
            show: false,
        },
        y: {
            title: {
                formatter: (formatter = () => {
                    return "";
                }),
            },
        },
    },
};
var chart = new ApexCharts(document.querySelector("#chart"), options);
chart.render();

// Chart Widget 2
var options = {
    series: [
        {
            data: [10, 82, 40, 65, 20, 89, 40, 20, 70, 98],
        },
    ],
    chart: {
        height: 60,
        type: "line",
        fontFamily: "Nunito, sans-serif",
        sparkline: {
            enabled: true,
        },
        dropShadow: {
            enabled: false,
        },
    },
    stroke: {
        curve: "smooth",
        width: 2,
    },
    colors: ["#f1416c"],
    grid: {
        padding: {
            top: 5,
            bottom: 5,
            left: 5,
            right: 5,
        },
    },
    tooltip: {
        x: {
            show: false,
        },
        y: {
            title: {
                formatter: (formatter = () => {
                    return "";
                }),
            },
        },
    },
};
var chart = new ApexCharts(document.querySelector("#chart2"), options);
chart.render();

// Chart Widget 3
var options = {
    series: [
        {
            data: [0, 82, 60, 65, 0, 10, 80, 20, 70, 98],
        },
    ],
    chart: {
        height: 60,
        type: "line",
        fontFamily: "Nunito, sans-serif",
        sparkline: {
            enabled: true,
        },
        dropShadow: {
            enabled: false,
        },
    },
    stroke: {
        curve: "smooth",
        width: 2,
    },
    colors: ["#50cd89"],
    grid: {
        padding: {
            top: 5,
            bottom: 5,
            left: 5,
            right: 5,
        },
    },
    tooltip: {
        x: {
            show: false,
        },
        y: {
            title: {
                formatter: (formatter = () => {
                    return "";
                }),
            },
        },
    },
};
var chart = new ApexCharts(document.querySelector("#chart3"), options);
chart.render();

// overview
var options = {
    series: [{
        name: 'Reservations',
        data: [44, 55, 57, 56, 61, 58, 63, 60, 66, 57, 56, 61]
    }],
    chart: {
        type: 'bar',
        height: 385,
        toolbar: {
            show: false,
        },
    },
    plotOptions: {
        bar: {
            horizontal: false,
            columnWidth: '40%',
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
        categories: ['15 Oct', '16 Oct', '17 Oct', '18 Oct', '19 Oct', '20 Oct', '21 Oct', '22 Oct', '23 Oct', '24 Oct', '25 Oct', '26 Oct'],
    },
    fill: {
        colors: ['#000']
      },
    fill: {
        opacity: 1
    },
};
var chart = new ApexCharts(document.querySelector("#overview"), options);
chart.render();

// pie chart
var options = {
    labels: ['Residential', 'Farm House', 'Commercial', 'Others'],
    series: [44, 55, 33, 10],
    chart: {
        type: 'donut',
        height: 400,
    },
    legend: {
        show: true,
        position: 'bottom',
        verticalAlign: 'bottom',
        align: 'center'
    },
};
var chart = new ApexCharts(document.querySelector("#pie"), options);
chart.render();

// analytics
var options = {
    labels: ['Residential', 'Farm House', 'Commercial', 'Row House', 'Others'],
    series: [14, 21, 10, 18, 5],
    chart: {
        type: 'polarArea',
        height: 400,
    },
    legend: {
        show: true,
        position: 'bottom',
        verticalAlign: 'bottom',
        align: 'center'
    },
    stroke: {
        colors: ['#fff']
    },
    fill: {
        opacity: 0.8
    },
};
var chart = new ApexCharts(document.querySelector("#analytics"), options);
chart.render();