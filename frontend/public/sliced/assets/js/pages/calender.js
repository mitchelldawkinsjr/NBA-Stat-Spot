/*
-------------------------------------------------------------------------
* Template Name    : Sliced Pro - Tailwind CSS Admin & Dashboard Template   * 
* Author           : SRBThemes                                              *
* Version          : 1.0.0                                                  *
* Created          : October 2024                                           *
* File Description : clander init Js File                                   *
*------------------------------------------------------------------------
*/

import { Calendar } from '@fullcalendar/core'
import dayGridPlugin from '@fullcalendar/daygrid'

const calendarEl = document.getElementById('calendar');

const calendar = new Calendar(calendarEl, {
  plugins: [dayGridPlugin],
  initialView: 'dayGridMonth'
});

calendar.render();