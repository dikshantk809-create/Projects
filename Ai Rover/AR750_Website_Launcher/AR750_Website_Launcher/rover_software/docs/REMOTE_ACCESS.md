# Opening the console from outside your house

At home you type the Pi's address and it works, because your phone and the Pi
are on the same wifi. From outside, they are not.

There are three ways to fix that. Two are good. One is the one everybody tries
first and is the reason home cameras end up on the internet.

---

## Do not do this: port forwarding

Forwarding port 8080 on your router puts the rover on the public internet.
Within a day, machines that do nothing but scan for open ports will find it.
From then on, the only thing between your rover and the whole world is one
password.

If you have already done it, undo it.

---

## The easy way: Tailscale (recommended)

Tailscale builds a small private network between your own devices. The rover is
not on the internet; it is only reachable from devices you have signed in
yourself. It is free for personal use and gets through almost any router
without configuration.

On the Pi:

```bash
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
```

It prints a link. Open it, sign in, done. `tailscale ip -4` gives the rover an
address like `100.x.y.z`.

Then install the Tailscale app on your phone, sign in with the same account,
and open `http://100.x.y.z:8080` from anywhere in the world.

Useful extra, once it is working:

```bash
sudo tailscale up --ssh          # ssh to the rover from your phone too
```

---

## The other good way: a Cloudflare tunnel

Use this if you want a proper web address like
`https://rover.yourname.com`, with a real certificate, and you already have a
domain on Cloudflare.

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 \
  -o cloudflared && chmod +x cloudflared && sudo mv cloudflared /usr/local/bin/
cloudflared tunnel login
cloudflared tunnel create ar750
cloudflared tunnel route dns ar750 rover.yourname.com
```

`~/.cloudflared/config.yml`:

```yaml
tunnel: ar750
credentials-file: /home/pi/.cloudflared/<the-id>.json
ingress:
  - hostname: rover.yourname.com
    service: http://localhost:8080
  - service: http_status:404
```

```bash
sudo cloudflared service install
```

This does open the console to anyone who knows the address, so with this route
you must also turn on Cloudflare Access (free for up to 50 people) so only your
own email can reach it. Without that, you are back to one password guarding a
machine that can drive itself and spray chemicals.

---

## Whichever way you choose

**Change the password first.** It starts as `admin` / `agrirover`, which is
public knowledge because it is written in this folder. Sign in, go to Settings,
change both the username and the password. The console makes you do this the
first time anyway.

**Use a long password.** Four unrelated words beat a short clever one. The
console slows down after six wrong tries from the same address, but that only
helps if the password is not guessable in six.

**Remember what you are exposing.** This is not a webcam. Whoever can sign in
can drive the rover, run the pump and start a patrol while you are out. Treat
the password the way you would treat a key to the shed.

**Think about what happens when the link drops.** If the phone loses signal
mid-drive, the rover stops by itself after about half a second, because nothing
is telling it to keep going. That is the dead man rule, and it is why driving
from a train is safe in the sense that it will not run away - though you still
should not do it, because you cannot see where it is going.
