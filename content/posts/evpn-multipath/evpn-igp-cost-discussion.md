# Verify EVPN route selection

> check the clab lab at ttl256-dev-3. as far as I understand without bgp multipath leaf1 picks a single evpn route from spines, then next hop is actually resolved into ecmp that isis made possible to do. but in show bgp evpn output it looks like both routes received from spines contibute to ecmp which is weird. how to verify which evpn route is chosen?

<details><summary>4 previous messages</summary>

> I’ll inspect leaf1’s EVPN paths and next-hop resolution on `ttl256-dev-3`, then compare the selected BGP path with what is installed in the routing and forwarding tables.
>
> <details><summary>Ran 5 commands, searched the web</summary>
>
> - Ran `pwd && rg --files -g AGENTS.md -g '*clab*' -g '*ssh*' -g '*README*' . /Users/ttl256/.ssh 2>/dev/null`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'hostname; pwd; command -v containerlab; docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'hostname; pwd; command -v containerlab; docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'`
>
> Searched the web for `site.arista.com EOS show bgp evpn detail ECMP contributor best path maximum-paths`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'docker exec clab-bridged-overlay-leaf1 Cli -p 15 -c "show running-config | section router bgp; show bgp evpn; show bgp evpn detail; show ip route; show isis neighbors; show interfaces Vxlan1"'`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = [
> 'show version',
> 'show running-config | section router bgp',
> 'show bgp evpn',
> 'show bgp evpn detail',
> 'show ip route',
> 'show isis neighbors',
> 'show interfaces Vxlan1',
> ]
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker', 'exec', 'clab-bridged-overlay-leaf1', 'Cli', '-p', '15', '-c', command], check=False)
> PY`
>
> Searched the web for `site.arista.com "ECMP contributor" "same" "next hop" ...`
>
> </details>
>
> Leaf1 currently marks the route received from **spine2 (`22.22.22.22`)** as `best`. Both copies have the same EVPN next hop, `2.2.2.10`, and IS-IS installs two paths to that address. I’m checking the `ECMP contributor` flags against the VXLAN forwarding state to explain why both copies carry them.
>
> <details><summary>Ran 2 commands, searched the web</summary>
>
> Searched the web for `https://www.arista.com/en/um-eos/eos-border-gateway-protocol-bgp`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = [
> 'show bgp instance',
> 'show running-config all | section router bgp',
> 'show bgp evpn route-type mac-ip 02bb.bbbb.bbbb detail',
> 'show bgp evpn route-type mac-ip 02bb.bbbb.bbbb detail | json',
> 'show vxlan address-table',
> 'show mac address-table address 02bb.bbbb.bbbb',
> 'show vxlan vtep',
> 'show ip route 2.2.2.10 detail',
> 'show ip hardware fib 2.2.2.10',
> ]
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker', 'exec', 'clab-bridged-overlay-leaf1', 'Cli', '-p', '15', '-c', command], check=False)
> PY`
>
> Searched the web for `'ECMP contributor' in https://www.arista.com/en/um-eos/eos-border-gateway-protocol-bgp`
>
> Searched the web for `site.arista.com "EVPN" "maximum-paths" "MAC" "default" ...`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = [
> 'show l2rib input bgp',
> 'show l2rib output',
> 'show ip route 2.2.2.10 fec',
> 'show vxlan flood vtep',
> 'show bgp evpn instance',
> ]
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker', 'exec', 'clab-bridged-overlay-leaf1', 'Cli', '-p', '15', '-c', command], check=False)
> PY`
>
> Searched the web for `Arista EVPN "maximum-paths 1" "ECMP" ...`
>
> </details>
</details>

I checked `clab-bridged-overlay-leaf1` on `ttl256-dev-3`. **The current best EVPN path is the copy received from spine2 (`22.22.22.22`).** Your understanding of the forwarding path matches the lab: one remote VTEP, reached through IS-IS ECMP.

Run this on leaf1:

```text
show bgp evpn route-type mac-ip 02bb.bbbb.bbbb detail
```

The relevant output is:

```text
2.2.2.10 from 22.22.22.22 (22.22.22.22)
  ... valid, internal, ECMP head, ECMP, best, ECMP contributor

2.2.2.10 from 11.11.11.11 (11.11.11.11)
  ... valid, internal, ECMP, ECMP contributor
```

**Look for `best` in the detailed output, or `>` in the compact output.** For a machine-readable check, append `| json`: spine2’s path has `routeType.active: true`; spine1’s has `false`. The remote IMET route also currently selects spine2.

The confusing part is real: this EOS build marks **both** copies as ECMP contributors, despite its effective configuration being:

```text
maximum-paths 1 ecmp 128
```

Arista documents the BGP path limit and the forwarding ECMP limit as separate parameters. [BGP command reference](https://www.arista.com/en/um-eos/eos-border-gateway-protocol-bgp)

Those contributor flags do **not** establish that each RR supplies a separate forwarding next hop. Both advertisements carry the same VTEP next hop, `2.2.2.10`. Here is what leaf1 actually installs:

```text
leaf1# show l2rib input bgp
02bb.bbbb.bbbb, VLAN 10, seq 1, pref 16, EVPN dynamic remote
   VTEP 2.2.2.10

leaf1# show ip route 2.2.2.10 detail
 I L2     2.2.2.10/32 [115/30] PM
           via 11.11.11.11, Ethernet1
           via 22.22.22.22, Ethernet2

leaf1# show ip route 2.2.2.10 fec
...
Next hops:
    via 11.11.11.11, Ethernet1
    via 22.22.22.22, Ethernet2
```

So the verified chain is **destination MAC → VTEP `2.2.2.10` → two IS-IS forwarding next hops**. Selecting spine2’s EVPN advertisement does not pin VXLAN traffic to spine2; packets can use either underlay path.

I haven’t established the implementation-specific reason EOS sets `c` on both duplicate advertisements with `maximum-paths 1`, but the best-path selection and installed next-hop group are unambiguous above.

> now i'm running another lab on the same host. 10.0.100.100 is an external ip address reachable via two edge leaves.&#x20;
>
> before maximum-paths 2 enabled
>
> ```typescript
> leaf1#show bgp evpn route-type ip-prefix 10.0.100.100/32
> BGP routing table information for VRF default
> Router identifier 1.1.1.1, local AS number 65000
> BGP routing table entry for ip-prefix 10.0.100.100/32, Route Distinguisher: 3.3.3.3:5000
>  Paths: 2 available
>   65001 5
>     3.3.3.10 from 11.11.11.11 (11.11.11.11)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, best
>       Originator: 3.3.3.3, Cluster list: 11.11.11.11
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:24:26:b9
>       VNI: 5000
>   65001 5
>     3.3.3.10 from 22.22.22.22 (22.22.22.22)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal
>       Originator: 3.3.3.3, Cluster list: 22.22.22.22
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:24:26:b9
>       VNI: 5000
> BGP routing table entry for ip-prefix 10.0.100.100/32, Route Distinguisher: 4.4.4.4:5000
>  Paths: 2 available
>   65001 5
>     4.4.4.10 from 11.11.11.11 (11.11.11.11)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, best
>       Originator: 4.4.4.4, Cluster list: 11.11.11.11
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:4d:e3:6d
>       VNI: 5000
>   65001 5
>     4.4.4.10 from 22.22.22.22 (22.22.22.22)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal
>       Originator: 4.4.4.4, Cluster list: 22.22.22.22
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:4d:e3:6d
>       VNI: 5000
> ```
>
> after
>
> ```typescript
> leaf1#show bgp evpn route-type ip-prefix 10.0.100.100/32
> BGP routing table information for VRF default
> Router identifier 1.1.1.1, local AS number 65000
> BGP routing table entry for ip-prefix 10.0.100.100/32, Route Distinguisher: 3.3.3.3:5000
>  Paths: 2 available
>   65001 5
>     3.3.3.10 from 11.11.11.11 (11.11.11.11)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, ECMP head, ECMP, best, ECMP contributor
>       Originator: 3.3.3.3, Cluster list: 11.11.11.11
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:24:26:b9
>       VNI: 5000
>   65001 5
>     3.3.3.10 from 22.22.22.22 (22.22.22.22)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, ECMP, ECMP contributor
>       Originator: 3.3.3.3, Cluster list: 22.22.22.22
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:24:26:b9
>       VNI: 5000
> BGP routing table entry for ip-prefix 10.0.100.100/32, Route Distinguisher: 4.4.4.4:5000
>  Paths: 2 available
>   65001 5
>     4.4.4.10 from 11.11.11.11 (11.11.11.11)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, ECMP head, ECMP, best, ECMP contributor
>       Originator: 4.4.4.4, Cluster list: 11.11.11.11
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:4d:e3:6d
>       VNI: 5000
>   65001 5
>     4.4.4.10 from 22.22.22.22 (22.22.22.22)
>       Origin IGP, metric -, localpref 100, weight 0, tag 0, valid, internal, ECMP, ECMP contributor
>       Originator: 4.4.4.4, Cluster list: 22.22.22.22
>       Extended Community: Route-Target-AS:65000:5000 TunnelEncap:tunnelTypeVxlan EvpnRouterMac:00:1c:73:4d:e3:6d
>       VNI: 5000
> ```
>
> how to tell that both 3.3.3.10 and 4.4.4.10 are used for ecmp in overlay?

<details><summary>4 previous messages</summary>

> I’ll check the new lab’s tenant VRF routing table and forwarding entries. That will show whether `10.0.100.100/32` uses both edge VTEPs after the EVPN routes are imported.
>
> <details><summary>Ran 3 commands, searched the web</summary>
>
> Searched the web for `site.arista.com "show ip route vrf" "VTEP" "VNI" "ECMP" ...`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'docker ps --format "{{.Names}}\t{{.Image}}\t{{.Status}}"'`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = ['show vrf', 'show running-config | section router bgp', 'show ip route vrf all 10.0.100.100/32', 'show bgp evpn route-type ip-prefix 10.0.100.100/32']
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker','exec','clab-external-routing-leaf1','Cli','-p','15','-c',command],check=False)
> PY`
>
> Searched the web for `https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = ['show ip bgp vrf CUSTOMER_A 10.0.100.100/32 detail', 'show ip route vrf CUSTOMER_A 10.0.100.100/32 fec', 'show ip route 3.3.3.10/32 fec', 'show ip route 4.4.4.10/32 fec']
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker','exec','clab-external-routing-leaf1','Cli','-p','15','-c',command],check=False)
> PY`
>
> </details>
>
> Both edge VTEPs are installed for `10.0.100.100/32` in `CUSTOMER_A`, and its forwarding group contains two VXLAN tunnel entries. Your EVPN output shows selection separately for each RD; the tenant VRF table is where you can verify ECMP across the two edge leaves.
>
> <details><summary>Ran 2 commands</summary>
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = ['show ip bgp 10.0.100.100/32 vrf CUSTOMER_A detail', 'show ip route vrf CUSTOMER_A 10.0.100.100/32']
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker','exec','clab-external-routing-leaf1','Cli','-p','15','-c',command],check=False)
> PY`
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = ['show ip bgp 10.0.100.100/32 vrf CUSTOMER_A', 'show ip bgp vrf CUSTOMER_A 10.0.100.100/32']
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker','exec','clab-external-routing-leaf1','Cli','-p','15','-c',command],check=False)
> PY`
>
> </details>
</details>

**Check the route in the importing IP VRF, `CUSTOMER_A`. I verified that leaf1 currently installs both VTEPs as overlay ECMP next hops.**

The clearest command is:

```text
leaf1# show ip route vrf CUSTOMER_A 10.0.100.100/32

 B I      10.0.100.100/32 [200/0]
           via VTEP 3.3.3.10 VNI 5000 router-mac 00:1c:73:24:26:b9 local-interface Vxlan1
           via VTEP 4.4.4.10 VNI 5000 router-mac 00:1c:73:4d:e3:6d local-interface Vxlan1
```

**Two `via VTEP` entries under the same tenant prefix confirm the installed overlay ECMP.** Its forwarding group also contains two tunnel next hops:

```text
leaf1# show ip route vrf CUSTOMER_A 10.0.100.100/32 fec

FEC ID 1297036705567604739, used by 1 IPv4 prefixes and 0 IPv6 prefixes
Next hops:
    via EVPN VXLAN tunnel index 1
    via EVPN VXLAN tunnel index 3
```

Your `show bgp evpn` output cannot establish this by itself because the different RDs make these **two separate EVPN route entries**:

- `RD 3.3.3.3:5000`: selection between the two RR copies advertising VTEP `3.3.3.10`.
- `RD 4.4.4.4:5000`: selection between the two RR copies advertising VTEP `4.4.4.10`.

Each entry can have its own `best`, even when the tenant ultimately installs only one VTEP. After import, both entries become candidates for the same IPv4 prefix in `CUSTOMER_A`; that is where selection **across the edge leaves** happens. [Arista documents this distinction and verification](https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability).

To inspect that BGP decision, use this exact syntax:

```text
show ip bgp 10.0.100.100/32 vrf CUSTOMER_A
```

Currently it shows four imported paths—two RR copies per VTEP—with both VTEP addresses marked as ECMP contributors. Those four advertisements produce **two distinct overlay forwarding next hops**.

Separately, I checked that each VTEP resolves through both spines:

```text
show ip route 3.3.3.10/32 fec
show ip route 4.4.4.10/32 fec
```

Both list `Ethernet1` and `Ethernet2`: **overlay ECMP chooses an edge VTEP; underlay ECMP provides paths to that VTEP.**

> why do spines (rrs) announce both routes? is it becasue of RD? usually each would pick a best and announce only that route

<details><summary>2 previous messages</summary>

> Yes—the different RDs are the key. I’ll check the protocol wording to explain how the RR’s per-route selection differs from selection after import into `CUSTOMER_A`.
>
> <details><summary>Searched the web</summary>
>
> Searched the web for `https://www.rfc-editor.org/rfc/rfc9136.html`
>
> </details>
</details>

**Yes—because the RDs differ.** Your rule still holds: normally an RR advertises one best path **per distinct BGP route**, rather than one per bare IP prefix. [RFC 4456 §6](https://www.rfc-editor.org/rfc/rfc4456.html#section-6)

For EVPN Type 5, the route key includes **RD, Ethernet Tag ID, prefix length, and IP prefix**. Therefore, your RRs see two distinct routes: [RFC 9136 §3.1](https://www.rfc-editor.org/rfc/rfc9136.html#section-3.1)

| EVPN route identity, abbreviated | Next hop |
|---|---|
| `RD 3.3.3.3:5000 + 10.0.100.100/32` | `3.3.3.10` |
| `RD 4.4.4.4:5000 + 10.0.100.100/32` | `4.4.4.10` |

Each RR chooses a best path for **each row** and reflects both rows. This needs neither Add-Path nor `maximum-paths 2` on the RR.

On leaf1, there are then two stages:

1. **EVPN table:** the two RDs remain separate. Each route has two copies, one from each RR.
2. **Import into `CUSTOMER_A`:** both match RT `65000:5000` and become candidates for the same tenant destination, `10.0.100.100/32`. The tenant’s BGP selection determines whether one or both VTEPs are installed.

That is the distinction: **RD distinguishes routes; RT controls which VRFs import them.**

If both edge leaves used the **same RD**, with the other route-key fields identical, their advertisements would compete at each RR. Without Add-Path, each RR would normally reflect only its winner. Both RRs could choose the same edge leaf, hiding the alternative from leaf1. Unique RDs preserve both edge-leaf routes through reflection, allowing leaf1 to perform the overlay ECMP selection.

> From the link you provided: "**Note:** This feature is available only with the multi-agent routing protocol model." What does it mean?

<details><summary>2 previous messages</summary>

> I’ll check what Arista means by “multi-agent” here and which routing model your lab is running.
>
> <details><summary>Ran a command, searched the web</summary>
>
> Searched the web for `site.arista.com EOS multi-agent routing protocol model ribd bgp agent service routing protocols model multi-agent ...`
>
> - Ran `ssh -o BatchMode=yes -o ConnectTimeout=10 ttl256-dev-3 'python3 -' <<'PY'
> import subprocess
> commands = ['show running-config | include service routing protocols', 'show running-config all | include service routing protocols', 'show version']
> for command in commands:
>     print('\n### ' + command, flush=True)
>     subprocess.run(['docker','exec','clab-external-routing-leaf1','Cli','-p','15','-c',command],check=False)
> PY`
>
> Searched the web for `https://www.arista.com/en/support/toi/tag/ribd`
>
> </details>
</details>

“Multi-agent” means **how EOS organizes its routing software inside a single switch**. An *agent* here is a software process.

EOS historically had two routing implementations:

| Model | Organization |
|---|---|
| **`ribd` / single-agent** | Routing protocols shared one routing-agent process. |
| **`multi-agent`** | Routing work is split into separate processes, such as BGP, IS-IS, and routing-table management. |

This separation improves process isolation and allows routing work to run independently. It is an EOS implementation choice, rather than a change to the BGP protocol. [Arista architecture documentation](https://www.arista.com/en/um-eos/eos-session-management-commands?searchword=eos+10+5+ethernet+configuration+procedures)

In the page you quoted, **“this feature” specifically means using the underlay IGP cost when selecting imported EVPN Type-5 routes**, enabled by:

```text
router bgp 65000
   address-family evpn
      encapsulation vxlan layer-3 set next-hop igp-cost
```

The note says that functionality requires the multi-agent implementation. [Feature documentation](https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability)

**Your lab already meets that requirement.** I checked leaf1:

```text
leaf1# show running-config all | include service routing protocols
service routing protocols model multi-agent
```

It runs EOS **4.36.2F**. Arista removed the older `ribd` model starting with **4.32.0F**, so multi-agent is the only routing model in your release. That note mainly matters when reading the documentation for older EOS versions. [Arista release information](https://www.arista.com/en/support/toi/tag/ribd)

> I understand the feature, but I don't get the use in the real world with symmetric fabric for dual homed servers/external connectivity. Usually the IGP cost is just the same

<details><summary>2 previous messages</summary>

> In a symmetric fabric, equal IGP costs usually make this feature irrelevant. I’ll check the deployment cases where costs differ and whether they apply to dual-homed servers or external connectivity.
>
> <details><summary>Searched the web</summary>
>
> Searched the web for `site.arista.com "IGP cost" "VTEP" "site" ...`
>
> </details>
</details>

**Yes—in a regular symmetric leaf–spine fabric, this feature usually changes nothing.** In your lab, both edge VTEPs had an IGP metric of `30`; enabling the comparison would preserve the tie and allow the same overlay ECMP.

Its purpose is to make **distance to the exit VTEP** influence selection when the topology is asymmetric. Arista’s example deliberately uses unequal underlay metrics to demonstrate this. [Feature documentation](https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability)

A practical use would be exits distributed across pods or locations, provided the underlay metrics reflect that distance. For example, with otherwise equal Type-5 advertisements:

| From a leaf in pod A | Cost to VTEP | Without the feature | With the feature |
|---|---:|---|---|
| Border leaf in pod A | 30 | ECMP candidate | Preferred |
| Border leaf in pod B | 70 | ECMP candidate | Alternative |

This lets each ingress leaf prefer its nearest exit. Another ingress leaf might prefer the opposite border. That differs from assigning one border a higher local preference everywhere, which establishes a common preference regardless of ingress location.

It can also matter after a failure **if the shortest remaining path to one VTEP becomes more expensive**—for example, it now requires a detour through another pod.

But your skepticism is especially valid for ordinary fabric failures:

- Losing one of several equal-cost uplinks often leaves the **minimum IGP cost unchanged**. The feature does nothing, even though available capacity decreased.
- It does not measure congestion, remaining bandwidth, or the quality of the external path beyond the border leaf.
- For dual-homed servers, this particular Type-5 feature is not what provides EVPN Ethernet-segment multihoming and load balancing.

For your two equally connected external-facing leaves, **there is no additional benefit while their costs remain equal**. The design decision is whether, should those costs diverge, you want to keep using both exits or prefer the nearer one. Either can be intentional: preferring the nearer exit saves internal transport, while keeping both may better use external capacity.

> In a regular ISP topology there's a place for overload or high metrics during bgp convergence process. That is to detour transit traffic from a device not having BGP converged yet otherwise it would create a blackhole for some traffic. As far as I understand the usual dc fabric a leaf is almost never a transit. While saying that I realised that it's true for valley-free fabrics... so, for a non-valley-free fabric, if leaf1 receives routes with nh of leaf2 and leaf3, and leaf2 is healthy one, while leaf3 can only be reached via a valley, without igp cost consideration leaf1 would form ECMP group with both nhs. sounds logical?

<details><summary>2 previous messages</summary>

> Yes—if the detour raises the IGP cost to leaf3, that is a concrete use for the feature. I’ll check one distinction: an IS-IS overload bit excludes a router from transit paths, but does not necessarily make its own VTEP address unreachable.
>
> <details><summary>Searched the web</summary>
>
> Searched the web for `site.juniper.net IS-IS overload bit directly connected prefixes reachable transit ...`
>
> </details>
</details>

**Yes—that scenario is a concrete use for it.** Assuming both leaves advertise the same Type-5 prefix, their earlier BGP attributes tie, and multipath is enabled:

| Overlay next hop | Available underlay path | Example IGP cost |
|---|---|---:|
| leaf2 | `leaf1 → spine1 → leaf2` | 30 |
| leaf3 | `leaf1 → spine1 → leaf2 → spine2 → leaf3` | 50 |

The second path contains a valley: down to leaf2, then back up to spine2.

- **Without IGP-cost consideration:** leaf1 can install overlay ECMP toward both leaf2 and leaf3. Traffic assigned to leaf3 takes that detour.
- **With it:** leaf1 prefers leaf2 because its VTEP has the lower underlay cost. Leaf3’s advertisement remains a nonselected candidate. This follows directly from the documented Type-5 selection behavior. [Arista documentation](https://www.arista.com/en/um-eos/eos-evpn-igp-cost-for-vtep-reachability)

The distinction is that **IS-IS finds the shortest path to each VTEP independently**. It cannot decide that the tenant destination should use leaf2 instead of leaf3. Importing the IGP cost into the tenant’s BGP selection enables that comparison across exits.

There are two qualifications to the convergence analogy:

**Underlay transit does not require tenant BGP convergence.** In that example, leaf2 can forward a VXLAN packet toward leaf3 using its outer destination address. It only needs underlay reachability to leaf3; it need not know the inner `10.0.100.100/32` route. Leaf2 does need the tenant forwarding state when it is itself the selected tunnel endpoint and external exit.

**The IS-IS overload bit protects against using a router as transit.** Its own directly attached prefixes—including its VTEP loopback—can remain reachable. Consequently, setting overload on leaf3 does not by itself prevent leaf1 from selecting leaf3 as an overlay exit. [IS-IS overload behavior](https://www.cisco.com/c/en/us/support/docs/ip/integrated-intermediate-system-to-intermediate-system-is-is/24509-set-overload-bit.html)

So your detour reasoning holds: **the feature can avoid a more expensive overlay exit when its underlay reachability degrades.** It reacts to the resulting metric difference; it does not directly detect valleys or whether the exit’s BGP has converged.
