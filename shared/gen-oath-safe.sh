#!/bin/bash

# Copyright (C) 2016 Thomas Zink <tz@uni.kn>
# Copyright (C) 2013 Richard Monk <rmonk@redhat.com>
# Originally from
# https://post-office.corp.redhat.com/mailman/private/memo-list\
#    /2013-February/msg00116.html
# Copyright (C) 2013-2014 Matěj Cepl <mcepl@cepl.eu>
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall
# be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF
# ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED
# TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR
# A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT
# SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR
# IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

function digitalRoot() {
    # Requires an input a string
    # JavaScript equivalent (for comparison):
    #
    # function digitalRoot(inNo) {
    #   var cipher_sum = Array.reduce(inNo, function(prev, cur) {
    #     return prev + cur.charCodeAt(0);
    #   }, 0);
    #   return cipher_sum % 10;
    # }

    sum=0
    n=$1
    i=0

    while [ $i -lt ${#n} ] ; do
        ord=$(echo -n ${n:$i:1}|od -An -td|tr -d '[:blank:]')
        sum=$(( sum + ord )) # calculate sum of digit
        i=$(( i + 1 ))
    done

    sum=$(( sum % 10 ))
}

echo

tempfile="$(mktemp)"

name="$1"

if [ -z "$name" ] || [[ "$name" =~ (-h|--help)  ]]; then
	echo "usage: $0 username [tokentype] [secret]"
	echo ""
	echo "Options:"
	echo "    tokentype: hotp | totp"
	echo "    secret: a hex encoded secret key"
	echo ""
    exit 1
fi

type="$2"
case "$type" in
    totp)
        tokentype="totp"
        tokenID="HOTP/T30"
    ;;
    hotp)
        tokentype="hotp"
        tokenID="HOTP"
    ;;
    *)
        echo "INFO: Bad or no token type specified, using TOTP."
        tokentype="totp"
        tokenID="HOTP/T30"
    ;;
esac

hexkey="$3"
if [ -z "$hexkey" ]; then
	echo "INFO: No secret provided, generating random secret."
	hexkey="$(openssl rand -hex 20)"
fi

if [[ ! "$hexkey" =~ ^[A-Fa-f0-9]*$ ]]; then
	echo "ERROR: Invalid secret, must be hex encoded."
	exit 1
fi

echo ""

b32key="$(echo -n "$hexkey" | python -c "import sys; import base64; import binascii; print(base64.b32encode(binascii.unhexlify(sys.stdin.read())))")"

digitalRoot $b32key && b32checksum=$sum

echo "Key in Hex: $hexkey"
echo "Key in b32: $b32key (checksum: $b32checksum)"
echo ""
echo "URI: otpauth://$tokentype/$1?secret=$b32key"

qrencode -m 1 -s 1 "otpauth://$tokentype/$1?secret=$b32key" -o $tempfile
filesize="$(file $tempfile | cut -d, -f2 | cut -d' ' -f2)"
img2txt -H $filesize -W $(( $filesize * 2)) $tempfile

if [ "$tokentype" == "hotp" ]; then
    echo ""
    echo "Yubikey setup (Slot 1):"
    echo "ykpersonalize -1 -ooath-hotp -ooath-imf=0 -ofixed= -oappend-cr -a$hexkey"
    echo "Yubikey setup (Slot 2):"
    echo "ykpersonalize -2 -ooath-hotp -ooath-imf=0 -ofixed= -oappend-cr -a$hexkey"
	algorithm="HOTP"
fi

if [ "$tokentype" == "totp" ]; then
	algorithm="HOTP/T30"
fi

echo ""
echo "users.oath / otp.users configuration:"
echo "$algorithm $name - $hexkey"

rm $tempfile