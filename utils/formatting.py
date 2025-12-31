def usd(x):
    return f"${x:,.2f}"

def mask_address(addr):
    return addr[:6] + "..." + addr[-4:]

