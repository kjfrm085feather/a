import discord
from discord.ext import commands
import subprocess
import re
import asyncio
import os

# ───────── CONFIG ─────────
TOKEN = "MTQ2NzMxMDQyNDg3Njc4MTY0Mg.GUJk0Z.lpCj1JX8TfUuVoWG7kV1n_tYfE0SnrR6oTdGj"
ADMIN_ID = 1383641747913183256 # Replace with your Discord ID

# ───────── BOT SETUP ─────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# ───────── VPS PLANS ─────────
PLANS = {
    "nano":    {"ram": "2G",  "storage": "10G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "basic":   {"ram": "2G",  "storage": "10G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "small":   {"ram": "4G",  "storage": "20G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "pro":     {"ram": "4G",  "storage": "40G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "medium":  {"ram": "6G",  "storage": "60G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "ultra":   {"ram": "8G",  "storage": "80G",  "template": "ubuntu", "release": "22.04", "cpu": 2},
    "large":   {"ram": "10G", "storage": "100G", "template": "ubuntu", "release": "22.04", "cpu": 2},
    "mega":    {"ram": "12G", "storage": "120G","template": "ubuntu", "release": "22.04", "cpu": 2},
    "xmega":   {"ram": "16G", "storage": "160G","template": "ubuntu", "release": "22.04", "cpu": 2},
    "titan":   {"ram": "32G", "storage": "200G","template": "ubuntu", "release": "22.04", "cpu": 2},
}

# ───────── HELPERS ─────────
def sanitize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "", text)

def get_container(username: str) -> str:
    base = f"VortexNodes-{username}"
    result = subprocess.getoutput(
        f"lxc-ls | grep '^{base}' | head -n1"
    )
    return result.strip()

def next_container_name(username: str) -> str:
    base = f"VortexNodes-{username}"
    existing = subprocess.getoutput(f"lxc-ls | grep '^{base}'").splitlines()
    return base if not existing else f"{base}-{len(existing)+1}"

# ───────── EVENTS ─────────
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ───────── COMMAND: .plans ─────────
@bot.command()
async def plans(ctx):
    embed = discord.Embed(title="📦 Available VPS Plans", color=discord.Color.blurple())
    for plan, specs in PLANS.items():
        embed.add_field(
            name=plan.capitalize(),
            value=f"🧠 RAM: {specs['ram']}\n💾 Storage: {specs['storage']}\n🖥 CPU: {specs['cpu']} cores",
            inline=False
        )
    await ctx.send(embed=embed)

# ───────── COMMAND: .create (Admin Only) ─────────
@bot.command()
async def create(ctx, member: discord.Member, plan: str):
    if ctx.author.id != ADMIN_ID:
        return await ctx.send(embed=discord.Embed(
            description="❌ You are not allowed to use this command.",
            color=discord.Color.red()
        ))

    plan = plan.lower()
    if plan not in PLANS:
        return await ctx.send(embed=discord.Embed(
            description=f"❌ Invalid plan.\nAvailable: {', '.join(PLANS)}",
            color=discord.Color.red()
        ))

    specs = PLANS[plan]
    username = sanitize(member.name)
    container_name = next_container_name(username)

    # LXC create
    try:
        # Create container
        subprocess.run([
            "lxc-create", "-n", container_name, "-t", "download", "--",
            "-d", specs['template'], "-r", specs['release'], "-a", "amd64"
        ], check=True)

        # Set RAM limit
        subprocess.run(["lxc-cgroup", "-n", container_name, "memory.limit_in_bytes", specs['ram']], check=True)
        # Set CPU cores (minimum 2)
        subprocess.run(["lxc-cgroup", "-n", container_name, "cpuset.cpus", ",".join(map(str, range(specs['cpu'])))], check=True)

        # TODO: Set storage via rootfs if your LXC setup supports (depends on storage backend)
        # subprocess.run(["resizefs or custom script"], check=True)

        # Start container
        subprocess.run(["lxc-start", "-n", container_name, "-d"], check=True)

        await ctx.send(embed=discord.Embed(
            title="✅ VPS Created",
            description=(
                f"👤 **User:** {member.mention}\n"
                f"📛 **Container:** `{container_name}`\n"
                f"📦 **Plan:** `{plan}`\n"
                f"🧠 **RAM:** {specs['ram']}\n"
                f"💾 **Storage:** {specs['storage']}\n"
                f"🖥 CPU cores: {specs['cpu']}"
            ),
            color=discord.Color.green()
        ))

    except subprocess.CalledProcessError:
        await ctx.send(embed=discord.Embed(
            description="❌ Failed to create VPS.",
            color=discord.Color.red()
        ))

# ───────── MANAGE VIEW ─────────
class ManageView(discord.ui.View):
    def __init__(self, member, container):
        super().__init__(timeout=None)
        self.member = member
        self.container = container

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(embed=discord.Embed(
                description="❌ You cannot manage someone else’s VPS.",
                color=discord.Color.red()
            ), ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
    async def start_btn(self, interaction: discord.Interaction, _):
        subprocess.run(["lxc-start", "-n", self.container, "-d"])
        await interaction.response.send_message(embed=discord.Embed(
            description="✅ VPS started.",
            color=discord.Color.green()
        ), ephemeral=True)

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, _):
        subprocess.run(["lxc-stop", "-n", self.container])
        await interaction.response.send_message(embed=discord.Embed(
            description="🛑 VPS stopped.",
            color=discord.Color.red()
        ), ephemeral=True)

    @discord.ui.button(label="Reinstall OS", style=discord.ButtonStyle.secondary)
    async def reinstall_btn(self, interaction: discord.Interaction, _):
        # Destroy container
        subprocess.run(["lxc-destroy", "-n", self.container])
        # Recreate with same plan specs
        plan_name = self.container.split("-")[1].lower()  # crude way, you could persist plan per container
        specs = PLANS.get(plan_name, {"ram":"2G","storage":"10G","template":"ubuntu","release":"22.04","cpu":2})

        subprocess.run([
            "lxc-create", "-n", self.container, "-t", "download", "--",
            "-d", specs['template'], "-r", specs['release'], "-a", "amd64"
        ])
        subprocess.run(["lxc-cgroup", "-n", self.container, "memory.limit_in_bytes", specs['ram']])
        subprocess.run(["lxc-cgroup", "-n", self.container, "cpuset.cpus", ",".join(map(str, range(specs['cpu'])))])
        subprocess.run(["lxc-start", "-n", self.container, "-d"])

        await interaction.response.send_message(embed=discord.Embed(
            description="♻️ VPS reinstalled (fresh OS).",
            color=discord.Color.orange()
        ), ephemeral=True)

    @discord.ui.button(label="SSH Link", style=discord.ButtonStyle.primary)
    async def ssh_btn(self, interaction: discord.Interaction, _):
        # Install tmate inside LXC
        subprocess.run([
            "lxc-attach", "-n", self.container, "--",
            "bash", "-c", "apt update && apt install -y tmate"
        ])

        # Create tmate session with socket
        subprocess.Popen([
            "lxc-attach", "-n", self.container, "--",
            "bash", "-c", "tmate -S /tmp/tmate.sock new-session -d && tmate -S /tmp/tmate.sock wait tmate-ready"
        ])
        await asyncio.sleep(3)
        ssh_link = subprocess.getoutput(
            f"lxc-attach -n {self.container} -- tmate -S /tmp/tmate.sock display -p '#{{tmate_ssh}}'"
        )

        await self.member.send(embed=discord.Embed(
            title="🔐 SSH Access",
            description=f"```{ssh_link}```",
            color=discord.Color.blue()
        ))
        await interaction.response.send_message(embed=discord.Embed(
            description="📩 SSH link sent to your DMs.",
            color=discord.Color.blurple()
        ), ephemeral=True)

# ───────── COMMAND: .manage ─────────
@bot.command()
async def manage(ctx):
    username = sanitize(ctx.author.name)
    container = get_container(username)

    if not container:
        return await ctx.send(embed=discord.Embed(
            title="❌ No VPS Found",
            description="You do not have an active VPS.",
            color=discord.Color.red()
        ))

    await ctx.send(embed=discord.Embed(
        title="🖥️ VPS Management",
        description=f"**Container:** `{container}`",
        color=discord.Color.blurple()
    ), view=ManageView(ctx.author, container))

# ───────── RUN BOT ─────────
bot.run(TOKEN)
