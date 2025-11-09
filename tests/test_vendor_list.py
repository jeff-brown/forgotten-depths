#!/usr/bin/env python3

import asyncio
import socket
import time

async def test_vendor_list():
    """Test the vendor list command"""
    print("Testing vendor list command...")

    # Create connection to server
    reader, writer = await asyncio.open_connection('localhost', 4000)

    try:
        # Wait for welcome message
        welcome = await reader.read(1024)
        print(f"Server welcome: {welcome.decode()}")

        # Send username with unique timestamp to create new character
        import time
        unique_username = f"user{int(time.time())}"
        print(f"Testing with username: {unique_username}")
        writer.write(f"{unique_username}\n".encode())
        await writer.drain()

        # Wait for response
        await asyncio.sleep(0.5)
        response = await reader.read(1024)
        print(f"Username response: {response.decode()}")

        # Send list command
        print("Sending 'list' command...")
        writer.write(b"list\n")
        await writer.drain()

        # Wait for response
        await asyncio.sleep(1)
        response = await reader.read(2048)
        result = response.decode()
        print(f"List command response:\n{result}")

        if "has the following items for sale" in result:
            print("✓ SUCCESS: Vendor list command working!")
        elif "There is no vendor here" in result:
            print("! INFO: No vendor in starting location (inn_entrance)")

            # Try going to market square where vendors are
            print("Moving to market_square...")
            writer.write(b"go east\n")
            await writer.drain()
            await asyncio.sleep(0.5)

            response = await reader.read(1024)
            print(f"Move response: {response.decode()}")

            # Try list again
            print("Trying list command in market_square...")
            writer.write(b"list\n")
            await writer.drain()
            await asyncio.sleep(1)

            response = await reader.read(2048)
            result = response.decode()
            print(f"Market square list response:\n{result}")

            if "has the following items for sale" in result:
                print("✓ SUCCESS: Vendor list command working in market_square!")
            else:
                print("✗ FAILED: List command still not working")
        else:
            print(f"✗ FAILED: Unexpected response: {result}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

if __name__ == "__main__":
    asyncio.run(test_vendor_list())