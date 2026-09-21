# Additional tool proposal

## `check_shipping_serviceability`

Add a read-only tool that accepts:

- origin country;
- destination country;
- shipment type, such as parcel, document, or freight.

It should return `serviceable`, supported service levels, restrictions, a rule
ID, policy version, and simulation marker. This gives the Rate Eligibility Agent
a useful second decision: determine whether the route is serviceable before
presenting a discount. It also prevents the eligibility function from growing
into a catch-all tool.

Keep it off the General Enquiry Agent so that agent remains intentionally
tool-free. Before implementation, define the country code format, synthetic
serviceability matrix, and whether serviceability is required before every rate
check or only when origin and destination are supplied.
