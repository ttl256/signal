---
date: '2026-11-13T22:25:43+03:00'
draft: false
title: 'BFD for EVPN BGP sessions'
tags: ["bfd", "bgp"]
---

BFD in the underlay helps to quickly identify the loss of connectivity when:
- There is an active device between peers and one side of the connection fails
- Unidirectional loss occurs on an optical link

Without BFD for EVPN BGP sessions, VTEPs might retain stale information until the BGP hold timer expires. In a valley-free fabric, it only takes one failed link to reproduce this behavior.

Consider a 3-stage Clos fabric with leaves dual homed to spines. BGP in the underlay has redistributed a primary loopback for multihop BGP EVPN sessions and a VTEP IP for VXLAN tunnels. Spines share the same AS65100 and preserve EVPN next hop on eBGP sessions. leaf1 and leaf2 participate in a bridged overlay to allow host1 and host2 to communicate in a layer 2 domain.

{{< figure
  src="bfd-for-evpn-bgp-base-topology.svg"
  align="center"
>}}

In the beginning the fabric is healthy. From leaf1's perspective, underlay and overlay BGP sessions are established, and host2's MAC address is learned from both spines via an EVPN Type 2 route with next hop 2.2.2.10.

```
leaf1#show bgp sum
BGP summary information for VRF default
Router identifier 1.1.1.1, local AS number 65001
Neighbor             AS Session State AFI/SAFI                AFI/SAFI State   NLRI Rcd   NLRI Acc   NLRI Adv
----------- ----------- ------------- ----------------------- -------------- ---------- ---------- ----------
11.11.11.11       65100 Established   L2VPN EVPN              Negotiated              2          2          2
22.22.22.22       65100 Established   L2VPN EVPN              Negotiated              2          2          4
169.254.0.0       65100 Established   IPv4 Unicast            Negotiated              3          3          3
169.254.0.4       65100 Established   IPv4 Unicast            Negotiated              3          3          5
```

```
leaf1#show bgp evpn route-type mac-ip 02:bb:bb:bb:bb:bb detail 
BGP routing table information for VRF default
Router identifier 1.1.1.1, local AS number 65001
BGP routing table entry for mac-ip 02bb.bbbb.bbbb, Route Distinguisher: 2.2.2.2:10
 Paths: 2 available
  65100 65002
    2.2.2.10 from 11.11.11.11 (11.11.11.11)
      Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, external, ECMP head, ECMP, best, ECMP contributor
      Extended Community: Route-Target-AS:65500:10010 TunnelEncap:tunnelTypeVxlan
      VNI: 10010 ESI: 0000:0000:0000:0000:0000
  65100 65002
    2.2.2.10 from 22.22.22.22 (22.22.22.22)
      Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, external, ECMP, ECMP contributor
      Extended Community: Route-Target-AS:65500:10010 TunnelEncap:tunnelTypeVxlan
      VNI: 10010 ESI: 0000:0000:0000:0000:0000
```

Let's shut down the link leaf1 <-> spine2. From spine2's perspective, the sequence of events is as follows:
- spine2 loses underlay connectivity to leaf1
- previously learned EVPN Type 2 routes become invalid due to an unresolvable next hop (VTEP IP 1.1.1.10). Assuming next hop resolution is enabled, which it is in the lab
- spine2 withdraws these EVPN Type 2 routes from leaf2

But from leaf1's perspective:
- leaf1 loses underlay connectivity to spine2
- the multihop BGP session doesn't automatically close and can remain established until the hold timer expires
- previously learned EVPN Type 2 routes from spine2 are still valid due to their next hop (VTEP IP 2.2.2.10) being resolvable via spine1

```
leaf1(config)#show bgp sum
BGP summary information for VRF default
Router identifier 1.1.1.1, local AS number 65001
Neighbor             AS Session State AFI/SAFI                AFI/SAFI State   NLRI Rcd   NLRI Acc   NLRI Adv
----------- ----------- ------------- ----------------------- -------------- ---------- ---------- ----------
11.11.11.11       65100 Established   L2VPN EVPN              Negotiated              2          2          2
22.22.22.22       65100 Established   L2VPN EVPN              Negotiated              2          2          4
169.254.0.0       65100 Established   IPv4 Unicast            Negotiated              3          3          2
169.254.0.4       65100 Idle          IPv4 Unicast            Configured              0          0          0
```

```
leaf1(config)#show bgp evpn route-type mac-ip 02:bb:bb:bb:bb:bb detail
BGP routing table information for VRF default
Router identifier 1.1.1.1, local AS number 65001
BGP routing table entry for mac-ip 02bb.bbbb.bbbb, Route Distinguisher: 2.2.2.2:10
 Paths: 2 available
  65100 65002
    2.2.2.10 from 11.11.11.11 (11.11.11.11)
      Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, external, ECMP head, ECMP, best, ECMP contributor
      Extended Community: Route-Target-AS:65500:10010 TunnelEncap:tunnelTypeVxlan
      VNI: 10010 ESI: 0000:0000:0000:0000:0000
  65100 65002
    2.2.2.10 from 22.22.22.22 (22.22.22.22)
      Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, external, ECMP, ECMP contributor
      Extended Community: Route-Target-AS:65500:10010 TunnelEncap:tunnelTypeVxlan
      VNI: 10010 ESI: 0000:0000:0000:0000:0000
```

One link failure creates an opportunity for stale state. In order to expose it, let's withdraw host2's route by shutting down the interface on leaf2.

{{< figure
  src="bfd-for-evpn-bgp-failure.svg"
  align="center"
>}}

- spine1 withdraws its copy. spine2 also receives the withdrawal from leaf2, but cannot deliver it to leaf1
- leaf1’s retained spine2 copy remains usable because its VTEP next hop still resolves
- leaf1 forwards VXLAN traffic for VNI 10010 even though it's dropped on leaf2

```
leaf1(config)#show bgp evpn route-type mac-ip 02:bb:bb:bb:bb:bb detail
BGP routing table information for VRF default
Router identifier 1.1.1.1, local AS number 65001
BGP routing table entry for mac-ip 02bb.bbbb.bbbb, Route Distinguisher: 2.2.2.2:10
 Paths: 1 available
  65100 65002
    2.2.2.10 from 22.22.22.22 (22.22.22.22)
      Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, external, best
      Extended Community: Route-Target-AS:65500:10010 TunnelEncap:tunnelTypeVxlan
      VNI: 10010 ESI: 0000:0000:0000:0000:0000
```

```
leaf1(config)#show vxlan address-table
          Vxlan Mac Address Table
----------------------------------------------------------------------

VLAN  Mac Address     Type      Prt  VTEP             Moves   Last Move
----  -----------     ----      ---  ----             -----   ---------
  10  02bb.bbbb.bbbb  EVPN      Vx1  2.2.2.10         1       0:00:42 ago
Total Remote Mac Addresses for this criterion: 1
```

This may look harmless, since delivery is impossible regardless of the stale state, but consider the same behavior in another topology. A server is dual-homed to an ESI LAG pair (leaf2, leaf3). One of the members (leaf2) withdraws Type 1 routes. leaf1 still considers leaf2 as an eligible next hop despite the surviving attachment through leaf3[^1]. The same goes for a server's route exported into EVPN as Type 5, with a stale path through leaf4 and working path through leaf5.

[^1]: Traffic still forwarded to leaf2 will be blackholed unless the local repair mechanism is in place

{{< figure
  src="bfd-for-evpn-bgp-extended.svg"
  align="center"
>}}

With overlay BFD enabled between leaves and spines, when a leaf's BFD timer expires, BFD reports that the session is down to the local BGP process. BGP stops the overlay session, closes the TCP session and removes paths learned through that BGP session.

Let's reset the lab to the initial healthy state. With a negotiated interval of 600 ms and a detection multiplier of 3, the BFD detection timeout was 1.8 seconds from the last received control packet. In this run, BGP went down approximately 1.5 seconds after the interface-down event.

```
leaf1#
2026-11-14T15:40:39.739837+00:00 leaf1 Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet2 (VRF default), changed state to down
2026-11-14T15:40:39.746543+00:00 leaf1 Bgp: %BGP-5-ADJCHANGE: peer 169.254.0.4 (VRF default AS 65100) old state Established event Stop new state Idle
2026-11-14T15:40:41.260848+00:00 leaf1 Bfd: %BFD-5-STATE_CHANGE: peer (vrf:default, ip:22.22.22.22, intf:, srcIp:1.1.1.1, type:multihop) LD 828823869 changed state from Up to Down diag CtrlTimeout
2026-11-14T15:40:41.262773+00:00 leaf1 Bgp: %BGP-5-ADJCHANGE: peer 22.22.22.22 (VRF default AS 65100) old state Established event Stop new state Idle
2026-11-14T15:40:41.264023+00:00 leaf1 Bgp: %BGP-3-NOTIFICATION: sent to neighbor 22.22.22.22 (VRF default AS 65100) 6/10 (Cease/BFD down <Hard Reset>) 0 bytes
```

```
leaf1#show bgp sum
BGP summary information for VRF default
Router identifier 1.1.1.1, local AS number 65001
Neighbor             AS Session State AFI/SAFI                AFI/SAFI State   NLRI Rcd   NLRI Acc   NLRI Adv
----------- ----------- ------------- ----------------------- -------------- ---------- ---------- ----------
11.11.11.11       65100 Established   L2VPN EVPN              Negotiated              2          2          2
22.22.22.22       65100 Active        L2VPN EVPN              Configured              0          0          0
169.254.0.0       65100 Established   IPv4 Unicast            Negotiated              3          3          2
169.254.0.4       65100 Idle          IPv4 Unicast            Configured              0          0          0
```
