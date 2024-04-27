# Wireguard Peer Monitoring

[![made-with-python](https://img.shields.io/badge/Made%20with-Python-1f425f.svg)](https://www.python.org/) [![GitHub release](https://img.shields.io/github/release/hatamiarash7/Wireguard-Peer-Monitoring.svg)](https://GitHub.com/hatamiarash7/Wireguard-Peer-Monitoring/releases/) [![Release](https://github.com/hatamiarash7/Wireguard-Peer-Monitoring/actions/workflows/release.yml/badge.svg)](https://github.com/hatamiarash7/Wireguard-Peer-Monitoring/actions/workflows/release.yml) ![GitHub](https://img.shields.io/github/license/hatamiarash7/wireguard-peer-monitoring)

This project uses [Linux kernel dynamic debug](https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html) features to capture and process Wireguard events and monitor peer activity.

This assumes that `debugfs` is mounted under `/sys/kernel/debug`.

The main purpose of this project is monitor Wireguard peers. Currently, It can be used to detect and handle `handshake` and `keepalive` events (You can handle more events, check [Events](#events) section).

All peer's information will be stored in Redis for further analysis. Also, notify the user when a peer's endpoint (IP, PORT) is updated.

These data will be stored in Redis for each peer:

- Endpoint's IP
- Endpoint's Port
- Last keepalive time
- Last handshake time

## How to

1. First, you need to enable Wireguard debug logs. You can do this by running the following command:

    ```bash
    echo 'module wireguard +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
    ```

2. Configure rsyslog to capture the logs. You can do this by adding the following line to `/etc/rsyslog.d/99-wireguard.conf`:

    ```bash
    kern.*  @127.0.0.1:9999
    ```

3. Create a new config file and fill it will proper data:

    ```bash
    cp config.example.toml config.toml
    ```

4. Run project to capture and handle events:

    ```bash
    CONFIG_FILE="config.toml" make run
    ```

    Or using Docker

    ```bash
    docker run -d -v $(pwd)/config.toml:/app/config.toml -p 9999:9999 hatamiarash7/wg-peer-monitoring:latest
    ```

## Events

There are many Wireguard events that can be captured. You can update the code to handle more events. Here are some of them:

- wg_cookie_message_consume: `Could not decrypt invalid cookie response`
- send4: `No route to <IP:PORT>, error <ERROR CODE>`
- send6: `No route to <IP:PORT>, error <ERROR CODE>`
- wg_receive_handshake_packet: `Receiving cookie response from <IP:PORT>`
- wg_receive_handshake_packet: `Invalid MAC of handshake, dropping packet from <IP:PORT>`
- wg_receive_handshake_packet: `Invalid handshake initiation from <IP:PORT>`
- wg_receive_handshake_packet: `Receiving handshake initiation from peer <PEER ID> (<IP:PORT>)`
- wg_receive_handshake_packet: `Invalid handshake response from <IP:PORT>`
- wg_receive_handshake_packet: `Receiving handshake response from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Receiving keepalive packet from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet has unallowed src IP <IP> from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet is neither ipv4 nor ipv6 from peer <PEER ID> (<IP:PORT>)`
- wg_packet_consume_data_done: `Packet has incorrect size from peer <PEER ID> (<IP:PORT>)`
- wg_packet_rx_poll: `Packet has invalid nonce <PEER ID> (max <PEER ID>)`
- wg_packet_receive: `Dropping handshake packet from <IP:PORT>`
- wg_packet_send_handshake_initiation: `Sending handshake initiation to peer <PEER ID> (<IP:PORT>)`
- wg_packet_send_handshake_response: `Sending handshake response to peer <PEER ID> (<IP:PORT>)`
- wg_packet_send_handshake_cookie: `Sending cookie response for denied handshake message for <IP:PORT>`
- wg_packet_send_keepalive: `Sending keepalive packet to peer <PEER ID> (<IP:PORT>)`
- wg_expired_retransmit_handshake: `Handshake for peer <PEER ID> (<IP:PORT>) did not complete after <TRY NUMBER> attempts, giving up`
- wg_expired_retransmit_handshake: `Handshake for peer <PEER ID> (<IP:PORT>) did not complete after <SEC> seconds, retrying (try <TRY NUMBER>)`
- wg_expired_new_handshake: `Retrying handshake with peer <PEER ID> (<IP:PORT>) because we stopped hearing back after <SEC> seconds`
- wg_queued_expired_zero_key_material: `Zeroing out all keys for peer <PEER ID> (<IP:PORT>), since we haven't received a new one in <SEC> seconds`
- wg_peer_create: `Peer <PEER ID> created`
- kref_release: `Peer <PEER ID> (<IP:PORT>) destroyed`
- wg_xmit: `Invalid IP packet`
- wg_xmit: `No peer has allowed IPs matching <IPv4>`
- wg_xmit: `No peer has allowed IPs matching <IPv6>`
- wg_xmit: `No valid endpoint has been configured or discovered for peer <PEER ID>`
- wg_destruct: `Interface destroyed`
- wg_newlink: `Interface created`
- wg_netns_pre_exit: `Creating namespace exiting`
- keypair_free_kref: `Keypair <PEER ID> destroyed for peer <PEER ID>`
- wg_noise_handshake_begin_session: `Keypair <PEER ID> created for peer <PEER ID>`

## Monitoring

You can use Prometheus to scrape internal metrics. You can configure your metric configuration in `config.toml` file.

- `metrics_host`: The host that the metrics server will listen on.
- `metrics_port`: The port that the metrics server will listen on.

Check <http://localhost:9998>. The following metrics are available:

- `wg_peer_monitoring_app_version_info`: The version information of the application.
- `wg_peer_monitoring_wg_wireguard_events_total`: The total number of Wireguard events per event's title and peer's ID.
- `wg_peer_monitoring_wg_wireguard_events_created`: The latest timestamp of Wireguard events that have been created. per event's title and peer's ID.

---

## Support 💛

[![Donate with Bitcoin](https://img.shields.io/badge/Bitcoin-bc1qmmh6vt366yzjt3grjxjjqynrrxs3frun8gnxrz-orange)](https://donatebadges.ir/donate/Bitcoin/bc1qmmh6vt366yzjt3grjxjjqynrrxs3frun8gnxrz) [![Donate with Ethereum](https://img.shields.io/badge/Ethereum-0x0831bD72Ea8904B38Be9D6185Da2f930d6078094-blueviolet)](https://donatebadges.ir/donate/Ethereum/0x0831bD72Ea8904B38Be9D6185Da2f930d6078094)

<div><a href="https://payping.ir/@hatamiarash7"><img src="https://cdn.payping.ir/statics/Payping-logo/Trust/blue.svg" height="128" width="128"></a></div>

## Contributing 🤝

Don't be shy and reach out to us if you want to contribute 😉

1. Fork it!
2. Create your feature branch: `git checkout -b my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin my-new-feature`
5. Submit a pull request

## Issues

Each project may have many problems. Contributing to the better development of this project by reporting them. 👍
