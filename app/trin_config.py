class TrinConfig:
    def __init__(self):
        self.storage = 100
        self.http_port = 8545
        self.history = True # Always enabled
        self.state = True
        self.beacon = True

    def get_trin_config(self):
        args = [
            f"--mb={self.storage}",
            "--web3-transport=http",
            "--web3-http-address=http://127.0.0.1:" + str(self.http_port),
        ]
        subnetworks = ["history"]
        if self.state:
            subnetworks.append("state")
        if self.beacon:
            subnetworks.append("beacon")
        subnetworks = "--portal-subnetworks=" + ",".join(subnetworks)
        args.append(subnetworks)
        return args

