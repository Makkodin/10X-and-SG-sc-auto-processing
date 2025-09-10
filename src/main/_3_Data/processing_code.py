import time

def wait_and_retry(wait_hours=8):
    wait_seconds = wait_hours * 3600
    
    print(f"\n\033[93m{'='*60}\033[0m")
    print(f"\033[93mAll flowcells processed. Waiting {wait_hours} hours...\033[0m")
    print(f"\033[93mNext check: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() + wait_seconds))}\033[0m")
    print(f"\033[93mPress Ctrl+C to exit\033[0m")
    print(f"\033[93m{'='*60}\033[0m")
    
    try:
        # Wait with periodic status updates
        for remaining in range(wait_seconds, 0, -300):  # Update every 5 minutes
            if remaining % 1800 == 0:  # Every 30 minutes
                hours_left = remaining // 3600
                mins_left = (remaining % 3600) // 60
                print(f"\033[93mTime left: {hours_left}h {mins_left}m\033[0m")
            time.sleep(300)
        
        print("\033[92mWaiting completed. Updating flowcells list...\033[0m")
        return True
        
    except KeyboardInterrupt:
        print("\n\033[91mInterrupted by user. Exiting...\033[0m")
        return False