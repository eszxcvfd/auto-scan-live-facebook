# Facebook Live Discovery

A tool that helps an operator discover Facebook livestreams that are live at a requested search moment. It distinguishes active broadcasts from recordings, replays, premieres, and archived videos.

## Language

**Live broadcast**:
A Facebook broadcast that is actively transmitting at the search moment.
_Avoid_: Recording, replay, premiere, archived video

**Search moment**:
The point in time when the user starts a search. A result is current only if its broadcast is active at that moment.
_Avoid_: Upload time, publication time

**Publicly discoverable livestream**:
A live broadcast exposed through Facebook's public discovery surfaces and eligible to appear in search results. The product treats discovery coverage as best-effort rather than complete coverage of Facebook.
_Avoid_: Every livestream on Facebook, private broadcast

**Discovery coverage**:
The set of publicly discoverable livestreams that the product can detect for a particular search. Coverage is not a claim that every live broadcast on Facebook has been found.
_Avoid_: Complete Facebook inventory

**Search query**:
At least one keyword or phrase supplied by the user to identify relevant live broadcasts. A search without a query is outside the product's initial scope.
_Avoid_: Unbounded Facebook scan

**Verified live broadcast**:
A live broadcast whose active state has been confirmed at a specific verification time. It is valid only for that moment and does not guarantee that the broadcast continues afterward.
_Avoid_: Permanently live result

**Discovery result**:
A verified live broadcast presented to the user with identifying metadata and a link to its Facebook page. The product does not copy, replay, or embed the broadcast as part of the result.
_Avoid_: In-app replay, recorded result

**Operator**:
The person who runs a keyword search to discover public Facebook broadcasts and chooses whether to open a result on Facebook.
_Avoid_: Viewer, administrator

**Live verification**:
The act of checking whether a discovered broadcast is actively transmitting at a specific search moment before presenting it as a discovery result.
_Avoid_: Assumed live status, historical live status
