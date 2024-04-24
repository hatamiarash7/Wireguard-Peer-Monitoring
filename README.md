# Wireguard Peer Monitoring

This project uses [Linux kernel dynamic debug](https://www.kernel.org/doc/html/latest/admin-guide/dynamic-debug-howto.html) features to capture and process Wireguard events and monitor peer activity.

This assumes that `debugfs` is mounted under `/sys/kernel/debug`.

## How to

1. First, you need to enable Wireguard debug logs. You can do this by running the following command:

    ```bash
    echo 'module wireguard +p' | sudo tee /sys/kernel/debug/dynamic_debug/control
    ```

2. Configure rsyslog to capture the logs. You can do this by adding the following line to `/etc/rsyslog.d/99-wireguard.conf`:

    ```bash
    kern.*  @127.0.0.1:9999
    ```
