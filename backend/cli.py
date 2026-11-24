import click
from flask.cli import with_appcontext

from .extensions import db
from .models import Site
from .services.activity import log_activity
from .validators import is_valid_domain, normalize_domain


@click.command("create-site")
@click.argument("name")
@click.argument("domain")
@with_appcontext
def create_site(name, domain):
    """Conecta um site: flask --app backend.app create-site "Minha Loja" minhaloja.com.br"""
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        raise click.ClickException("Domínio inválido.")
    if Site.query.filter_by(domain=domain).first():
        raise click.ClickException("Domínio já cadastrado.")
    site = Site(name=name, domain=domain)
    db.session.add(site)
    db.session.flush()
    log_activity("site.created", "site", site.id, f"{name} ({domain})", actor="cli")
    db.session.commit()
    click.echo(f"Site criado. Chave pública: {site.api_key}")


def register(app):
    app.cli.add_command(create_site)
