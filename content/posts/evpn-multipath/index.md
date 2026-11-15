---
date: '2026-11-15T16:59:04+03:00'
draft: true
title: 'EVPN Multipath'
---

## Plan

- Show ECMP in the underlay for a single-homed external connection
- Dual-home the server, don't enable multipath, show a single best path that BGP have chosen
- Enable multipath, show ECMP in the overlay
- EVPN IGP Cost for VTEP Reachability https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability
  - Show an example of non-optimal ECMP in the overlay in case of a non-valley-free fabric and a transit leaf
  - Show how configuring EVPN IGP cost for VTEP reachability helps. Expect EVPN route to have a single next hop to the healthy VTEP
  - [Discussion with Codex](evpn-igp-cost-discussion.md)
