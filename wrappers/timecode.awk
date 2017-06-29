BEGIN {
	counter = 100000001
	last_ts = 0
}
{
	current_ts = systime()
	if (current_ts == last_ts){
		counter += 1
		print current_ts "." counter
		print $0
	} else {
		counter = 100000001
		last_ts = current_ts
		print current_ts "." counter
		print $0
	}
	fflush()
}
