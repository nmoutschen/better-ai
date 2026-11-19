from units import km_to_miles, miles_to_km

assert abs(km_to_miles(10) - 6.21371) < 0.001, km_to_miles(10)
assert abs(km_to_miles(1.609344) - 1) < 1e-9, km_to_miles(1.609344)
assert abs(miles_to_km(10) - 16.09344) < 1e-9, miles_to_km(10)
