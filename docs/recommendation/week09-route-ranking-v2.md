# Week 09 Best-3 Route-pair Ranking v2

Related issue: #80

## Why route pairs

The user does not choose an origin station independently from a destination
station. A usable recommendation must have both a bike at the origin and an
empty dock at the destination while keeping the complete journey reasonable.

## Score

The existing station recommendation score already combines walking distance
and future availability. Route v2 adds complete-route convenience:

```text
route_score
  = 0.35 × origin_station_score
  + 0.35 × destination_station_score
  + 0.15 × eta_score
  + 0.15 × walking_score

eta_score = 1 - min(total_eta_min / 90, 1)
walking_score = 1 - min((walk_origin + walk_destination) / 20, 1)
```

Weights and normalization limits are backend configuration properties. They
are engineering defaults and must be validated in Week 10 rather than tuned
on the final hold-out result.

## Deterministic ordering

1. route score descending;
2. total ETA ascending;
3. total walking time ascending;
4. origin station ID ascending;
5. destination station ID ascending.

Routes with missing origin or destination recommendation scores are excluded.
The same station cannot be both route endpoints. Fewer than three valid routes
are returned as-is.

## Response explanation

Every route exposes the total score, four score components, and a deterministic
reason. The LLM may verbalize this structured result but cannot change the
score or ranking.
