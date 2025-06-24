# Notifications

Notifications in Compost are asynchronous messages. Currently, the most
mature use case is when some device wants to notify a client (typically a PC
application) about some event, without a prior request. There are many scenarios
where this is desirable, for example when the application needs to be notified
about a sudden error that happened on the device, or when device continuously
streams data from some sensor.

The only way the notification message frames differ from those produced by
response and requests during RPC call, is that the header field `TXN` will be
set to **0**.

```{tip}
It would also be a completely valid scenario to send notifications in the other direction. However,
two-way notifications are not yet fully supported by all implementations.
```

## Definition

Similarly to how RPC call is defined, you specify your signature as an empty
Python function and provide a `@notification` decorator which specifies
the message type.

```{important}
Currently, a notification call can only have a single parameter. For that 
reason, if you need to send multiple values, they need to be wrapped in 
a `struct`. In the example, `Date` contains
members for day, month and year.
```

```{code-block} python
:caption: Notification in protocol definition

@struct
class Date:
    day: U16
    month: U8
    year: I32

class NotificationProtocol(Protocol):
    @notification(0xE00)
    def notify_date(self, date: Date):
        """Notifies a current date."""
```

## Using notifications

To receive a notification defined in the protocol, you must first create a
custom handler with the same signature. If you access the notification through
instantiated protocol, it will have `subscribe(handler)` and
`unsubscribe(handler)` methods. These methods will allow you to register your
custom handler, so that it is executed each time the notification is received.

```{code-block} python
:caption: Subscribing to notification

transport = None # Initialize one of supported transports
dev = NotificationProtocol(transport)

def date_notif_handler(date: Date):
    print(date)

dev.notify_date.subscribe(date_notif_handler)
```

To send a notification from a C code, you must perform these actions:

1. Create a notification argument, in our case instance of `struct Date`.
2. Call the generated serialization function to convert the argument into a
   a proper Compost message
3. Send the buffer with the message over the transport

The approach for argument initialization will differ depending on the contents
of the structure. If all of the members are primitive types, as is the case of
our `Date` struct, it does not matter how the structure is initialized. You may
use the C-style block initialization for example.

```{code-block} c
:caption: C definition of Date structure

struct Date {
    uint16_t day;
    uint8_t month;
    int32_t year;
};
```

With the `Date` instance ready, simply use the provided serialization function
and call it with the `Date` instance. It accepts pointer to the message buffer
and its size as first two parameters, value of notification argument is last.

```{code-block} c
:caption: Notification call

#include "compost.h"

uint8_t tx_buf[1024];

int main(void)
{
    struct Date a = {
        .day = 1, 
        .month = 1,
        .year = 2025
    };
    int tx_len = notify_date_ser(tx_buf, sizeof(tx_buf), &date);
    // Send tx_len bytes from tx_buf over the selected transport
}
```

### Variable-size arguments

Situation is a bit more complicated when the notification arguments contain lists. 
In that case, the size of the entire structure is not fixed. If the user creates 
these member lists in the arbitrary location in the memory, **the store
function will have to copy all elements into the buffer!** This may or may not
be desirable, but for the optimal zero-copy approach, those lists should already
exist at the correct position in the buffer when the stor function is called.

This position is not always fixed, especially with multiple list members and
frequently changing list sizes. Therefore you need to allocate the structure
with the help of an allocator, similarly to how you create lists in the RPC
implementations. The difference is that you will obtain allocator in RPC, but
for notifications you need to create it yourself. Fortunately, there is a helper
function which makes the process easier.

Let's consider a following structure, which is an example of a reflow oven
soldering profile. Such profile would probably contain list of numbers, which
represent different temperatures over time. There could be one other member to
specify the time between temperature changes in seconds. The programmer might
choose to only support profiles with fixed number of temperature points, but it
is also not a problem for Compost to support profiles that differ in how many
points are needed to express the optimal temperature curve.

```{code-block} c
:caption: C definition of SolderingProfile structure

struct SolderingProfile {
    uint16_t step_seconds;
    struct CompostSliceI16 temps;
};
```

To make the initialization less intimidating, there are helper functions for
every structure that contains list members. `SolderingProfile_alloc_init` helper
is used to setup the allocator, and the `SolderingProfile_init` is use to
initialize every member list to a certain size.

```{code-block} c
:caption: Notification call with variable-size struct

#include "compost.h"

uint8_t tx_buf[1024];

int main(void)
{
    struct CompostAlloc alloc = SolderingProfile_alloc_init(tx_buf, sizeof(tx_buf));
    // Let's make a profile with 20 temperature points, spaced 60 seconds apart
    // Sequence will be 0, 10, 20, 30, 40...
    struct SolderingProfile profile = SolderingProfile_init(&alloc, 20);
    profile.step_seconds = 60;
    for (int i = 0; i < 20; i++)
        compost_slice_set(profile.temps, i, i*10);
    // Once the notification argument is setup, it can be serialized as usual
    int tx_len = notify_soldering_profile_ser(tx_buf, sizeof(tx_buf), &profile);
    // Send tx_len bytes from tx_buf over the selected transport
}
```

The obvious drawback of the above approach is that the size of member lists must
be known before the `SolderingProfile_init` is called. This is not always
possible, but fortunately nothing prevents you from using the
`compost_slice_new` directly.

```{warning}
When the helper function is not used, the list members **must** be initialized in the order of definition. Initialization **must** be performed for **all** list members.
```
