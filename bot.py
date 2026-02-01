import discord
from discord.ext import commands
import subprocess
import re
import asyncio

# ───────── CONFIG ─────────

TOKEN = "PUT_BOT_TOKEN_HERE"
ADMIN_ID = 123456789012345678  # YOUR Discord ID

# ───────── BOT SETUP ─────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

# ───────── PLANS (CPU / RAM / STORAGE) ─────────

PLANS = {
    "basic": {
        "cpus": "1",
        "ram": "1g",
        "storage": "10g"
    },
    "pro": {
        "cpus": "2",
        "ram": "2g",
        "storage": "25g"
    },
    "ultra": {
        "cpus": "4",
        "ram": "4g",
        "storage": "50g"
    }
}

# ───────── HELPERS ─────────

def sanitize(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9-]", "", text)

def get_container(username: str) -> str:
    base = f"VortexNodes-{username}"
    result = subprocess.getoutput(
        f"docker ps -a --format '{{{{.Names}}}}' | grep '^{base}' | head -n 1"
    )
    return result.strip()

def next_container_name(username: str) -> str:
    base = f"VortexNodes-{username}"
    existing = subprocess.getoutput(
        f"docker ps -a --format '{{{{.Names}}}}' | grep '^{base}'"
    ).splitlines()
    return base if not existing else f"{base}-{len(existing)+1}"

# ───────── EVENTS ─────────

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# ───────── ADMIN CREATE ─────────

@bot.command()
async def create(ctx, member: discord.Member, plan: str):
    if ctx.author.id != ADMIN_ID:
        return await ctx.send(
            embed=discord.Embed(
                description="❌ You are not allowed to use this command.",
                color=discord.Color.red()
            )
        )

    plan = plan.lower()
    if plan not in PLANS:
        return await ctx.send(
            embed=discord.Embed(
                description=f"❌ Invalid plan.\nAvailable: {', '.join(PLANS)}",
                color=discord.Color.red()
            )
        )

    username = sanitize(member.name)
    container_name = next_container_name(username)
    p = PLANS[plan]

    cmd = [
        "docker", "run", "-dit",
        "--name", container_name,
        "--cpus", p["cpus"],
        "--memory", p["ram"],
        "--storage-opt", f"size={p['storage']}",
        "ubuntu", "sleep", "infinity"
    ]

    try:
        subprocess.run(cmd, check=True)
        await ctx.send(
            embed=discord.Embed(
                title="✅ VPS Created",
                description=(
                    f"👤 **User:** {member.mention}\n"
                    f"📛 **Container:** `{container_name}`\n"
                    f"📦 **Plan:** `{plan}`\n"
                    f"🧠 **RAM:** `{p['ram']}`\n"
                    f"💾 **Storage:** `{p['storage']}`"
                ),
                color=discord.Color.green()
            )
        )
    except subprocess.CalledProcessError:
        await ctx.send(
            embed=discord.Embed(
                description="❌ Failed to create VPS.",
                color=discord.Color.red()
            )
        )

# ───────── MANAGE VIEW ─────────

class ManageView(discord.ui.View):
    def __init__(self, member, container):
        super().__init__(timeout=None)
        self.member = member
        self.container = container

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.member.id:
            await interaction.response.send_message(
                embed=discord.Embed(
                    description="❌ You cannot manage someone else’s VPS.",
                    color=discord.Color.red()
                ),
                ephemeral=True
            )
            return False
        return True

    @discord.ui.button(label="Start", style=discord.ButtonStyle.primary)
    async def start_btn(self, interaction: discord.Interaction, _):
        subprocess.run(["docker", "start", self.container])
        await interaction.response.send_message(
            embed=discord.Embed(
                description="✅ VPS started.",
                color=discord.Color.green()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Stop", style=discord.ButtonStyle.danger)
    async def stop_btn(self, interaction: discord.Interaction, _):
        subprocess.run(["docker", "stop", self.container])
        await interaction.response.send_message(
            embed=discord.Embed(
                description="🛑 VPS stopped.",
                color=discord.Color.red()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="Reinstall OS", style=discord.ButtonStyle.secondary)
    async def reinstall_btn(self, interaction: discord.Interaction, _):
        subprocess.run(["docker", "rm", "-f", self.container])
        subprocess.run([
            "docker", "run", "-dit",
            "--name", self.container,
            "--memory", "1g",
            "--storage-opt", "size=10g",
            "ubuntu", "sleep", "infinity"
        ])
        await interaction.response.send_message(
            embed=discord.Embed(
                description="♻️ VPS reinstalled (fresh OS).",
                color=discord.Color.orange()
            ),
            ephemeral=True
        )

    @discord.ui.button(label="SSH Link", style=discord.ButtonStyle.primary)
    async def ssh_btn(self, interaction: discord.Interaction, _):
        subprocess.run([
            "docker", "exec", self.container,
            "bash", "-c",
            "apt update && apt install -y tmate"
        ])

        subprocess.Popen([
            "docker", "exec", "-it",
            self.container, "tmate", "-F"
        ])

        await asyncio.sleep(3)

        ssh_link = subprocess.getoutput(
            f"docker exec {self.container} tmate display -p '#{{tmate_ssh}}'"
        )

        await self.member.send(
            embed=discord.Embed(
                title="🔐 SSH Access",
                description=f"```{ssh_link}```",
                color=discord.Color.blue()
            )
        )

        await interaction.response.send_message(
            embed=discord.Embed(
                description="📩 SSH link sent to your DMs.",
                color=discord.Color.blurple()
            ),
            ephemeral=True
        )

# ───────── USER MANAGE ─────────

@bot.command()
async def manage(ctx):
    username = sanitize(ctx.author.name)
    container = get_container(username)

    if not container:
        return await ctx.send(
            embed=discord.Embed(
                title="❌ No VPS Found",
                description="You do not have an active VPS.",
                color=discord.Color.red()
            )
        )

    await ctx.send(
        embed=discord.Embed(
            title="🖥️ VPS Management",
            description=f"**Container:** `{container}`",
            color=discord.Color.blurple()
        ),
        view=ManageView(ctx.author, container)
    )

bot.run(TOKEN)
