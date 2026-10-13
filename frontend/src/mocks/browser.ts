import {
  setupWorker,
} from 'msw/browser'

import {
  handlers,
} from './handlers'
import {
  stationHandlers,
} from './stationHandlers'

export const worker =
  setupWorker(
    ...handlers,
    ...stationHandlers,
  )
